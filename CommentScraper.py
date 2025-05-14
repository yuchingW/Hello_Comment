from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os
import pandas as pd
import time

def setup_youtube_api():
    """Setup YouTube API client with error handling"""
    load_dotenv()
    api_key = os.getenv('API_KEY')
    if not api_key:
        raise ValueError("API_KEY not found in .env file")
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        # print("api_key: ",api_key)
        return youtube
    except Exception as e:
        raise Exception(f"Failed to build YouTube API client: {str(e)}")

def get_playlist_id(url):
    """Extract playlist ID from URL with validation"""
    try:
        return url.split('list=')[1]
    except IndexError:
        raise ValueError("Invalid YouTube playlist URL")

def get_videos_from_playlist(playlist_id, youtube, limit=None):
    """Get videos from playlist with error handling and rate limiting"""
    videos = []
    next_page_token = None
    
    try:
        while True:
            try:
                playlist_items_response = youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                # Extract video information
                for video in playlist_items_response.get('items', []):
                    try:
                        video_id = video['snippet']['resourceId']['videoId']
                        
                        # Get video statistics
                        video_response = youtube.videos().list(
                            part="statistics",
                            id=video_id
                        ).execute()
                        
                        videos.append({
                            'title': video['snippet']['title'],
                            'video_id': video_id,
                            'description': video['snippet']['description'],
                            'published_at': video['snippet']['publishedAt'],
                            'view_count': video_response['items'][0]['statistics'].get('viewCount', 0),
                            'comment_count': video_response['items'][0]['statistics'].get('commentCount', 0)
                        })
                        
                        # Rate limiting
                        time.sleep(0.1)
                        
                    except KeyError as e:
                        print(f"Error extracting video data: {str(e)}")
                        continue
                
                next_page_token = playlist_items_response.get('nextPageToken')
                if not next_page_token or (limit and len(videos) >= limit):
                    break
                    
            except HttpError as e:
                if e.resp.status in [403, 429]:  # Quota exceeded or rate limit
                    if e.resp.status in [429]:
                        print("Rate limit exceeded. Waiting for 60 seconds...")
                    elif e.resp.status in [403]:
                        print("Quota exceeded.")

                    else:
                        print(f"HTTP error: {e.resp.status}")

                    time.sleep(60)
                    continue
                raise
                
        return pd.DataFrame(videos)
        
    except Exception as e:
        raise Exception(f"Error getting videos from playlist: {str(e)}")


def get_video_comments(youtube, video_id, video_title):
    comment_list = []
    next_page_token = None
    
    try:
        while True:
            try:
                # 獲取主留言
                comment_response = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page_token
                ).execute()

                time.sleep(3)

                # 處理每個主留言
                for item in comment_response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']
                    comment_data = [
                        video_title,
                        comment['textDisplay'],
                        comment['publishedAt'],
                        comment['authorDisplayName'],
                        comment['likeCount'],
                        'top_comment'
                    ]
                    # print(f">>> processing comment: {comment_data[1][:10]}")
                    comment_list.append(comment_data)

                    # 檢查是否有回覆留言
                    if item['snippet']['totalReplyCount'] > 0:
                        try:
                            parent_id = item['id']
                            reply_response = youtube.comments().list(
                                part="snippet",
                                maxResults=100,
                                parentId=parent_id
                            ).execute()

                            # 處理回覆留言
                            for reply in reply_response['items']:
                                reply_data = [
                                    video_title,
                                    reply['snippet']['textDisplay'],
                                    reply['snippet']['publishedAt'],
                                    reply['snippet']['authorDisplayName'],
                                    reply['snippet']['likeCount'],
                                    'reply'
                                ]
                                comment_list.append(reply_data)

                        except HttpError as e:
                            print(f"Error getting replies for comment {parent_id}: {str(e)}")
                            continue

                # 檢查是否有下一頁
                next_page_token = comment_response.get('nextPageToken')
                if not next_page_token:
                    break

                # 加入延遲避免超過 API 限制
                time.sleep(2)

            except HttpError as e:
                if e.resp.status in [403, 429]:
                    print("API quota exceeded or rate limit reached. Waiting...")
                    time.sleep(60)
                    continue
                raise

    except Exception as e:
        print(f"Error processing comments for video {video_id}: {str(e)}")
    
    return comment_list

def main():
    try:
        # Setup YouTube API
        youtube = setup_youtube_api()
        
        # # Get playlist videos
        # url = "https://www.youtube.com/playlist?list=PLnPLskqK8ToBl54cPR0HWaYaL_wcBHmrf"
        # playlist_id = get_playlist_id(url)
        # print(f"Processing playlist: {playlist_id}")
        
        # # Get video data
        # video_df = get_videos_from_playlist(playlist_id, youtube)
        # video_df.to_csv('data/all_videos_0430.csv', index=False)
        # print("All videos saved to all_videos_df.csv")
        # exit()

        filtered_df = pd.read_csv('data/videoList_0430.csv')
        # print(f"一共有,{len(filtered_df)}部影片")
        # print(video_df.head(2))
        # exit()
        
        # 抓取所有影片的留言
        all_comments = []
        for index, row in filtered_df.iterrows():
            print(f">>> Getting comments in {row['title']}")
            video_comments = get_video_comments(youtube, row['video_id'], row['title'])
            all_comments.extend(video_comments)
            print(f">>> Found {len(video_comments)} comments ")
        
            # 將留言存成 DataFrame 並儲存
            comments_df = pd.DataFrame(all_comments, columns=[
                'video_title',
                'comment_text',
                'published_at',
                'author_name',
                'like_count',
                'comment_type'
            ])
            
            comments_df.to_csv(f"data/comments/{index+31}_comments.csv", index=False, encoding='utf-8-sig')
            print(f"Total {len(comments_df)} comments saved as {index+31}_comments.csv")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
    # df = pd.read_csv('data/comments/eiBJmdjTOwU.csv')