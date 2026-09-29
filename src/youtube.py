import json,os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
SCOPES=['https://www.googleapis.com/auth/youtube.upload']
def upload_video(path,title,description,category,privacy):
    raw=os.environ.get('YOUTUBE_TOKEN_JSON')
    if not raw: raise RuntimeError('Missing YOUTUBE_TOKEN_JSON secret')
    creds=Credentials.from_authorized_user_info(json.loads(raw),SCOPES)
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request; creds.refresh(Request())
    y=build('youtube','v3',credentials=creds)
    body={'snippet':{'title':title[:95],'description':description,'categoryId':category},'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':False}}
    return y.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(path),chunksize=-1,resumable=True)).execute()['id']
