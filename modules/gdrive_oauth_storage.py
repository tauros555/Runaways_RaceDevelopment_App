from __future__ import annotations
import io, os, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
import pandas as pd

SCOPES=["https://www.googleapis.com/auth/drive"]

@dataclass
class OAuthDriveStatus:
    enabled: bool
    connected: bool
    mode: str
    folder_id: str|None
    history_file_id: str|None
    message: str

class GoogleDriveOAuthStorage:
    def __init__(self,secrets=None,session_state=None):
        try: self.cfg=dict(secrets.get("gdrive_oauth",{})) if secrets is not None else {}
        except Exception: self.cfg={}
        self.session_state=session_state
        self.enabled=bool(self.cfg.get("enabled",False))
        self.client_id=str(self.cfg.get("client_id","") or "").strip()
        self.client_secret=str(self.cfg.get("client_secret","") or "").strip()
        self.redirect_uri=str(self.cfg.get("redirect_uri","") or "").strip()
        self.folder_id=str(self.cfg.get("folder_id","") or "").strip()
        self.history_filename=str(self.cfg.get("history_filename","history_master.csv.gz"))
        self.backup_folder_name=str(self.cfg.get("backup_folder_name","backup"))
        self.log_filename=str(self.cfg.get("log_filename","update_log.csv"))
        self._service=None
    def configured(self): return all([self.enabled,self.client_id,self.client_secret,self.redirect_uri,self.folder_id])
    def _tok(self):
        if self.session_state is not None:
            t=self.session_state.get('_gdrive_oauth_token')
            if isinstance(t,dict): return dict(t)
        rt=str(self.cfg.get('refresh_token','') or '').strip()
        return {'refresh_token':rt} if rt else {}
    def authorization_url(self,state='race-development'):
        p={'client_id':self.client_id,'redirect_uri':self.redirect_uri,'response_type':'code','scope':' '.join(SCOPES),'access_type':'offline','include_granted_scopes':'true','prompt':'consent','state':state}
        return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(p)
    def exchange_code(self,code):
        import requests
        r=requests.post('https://oauth2.googleapis.com/token',data={'code':code,'client_id':self.client_id,'client_secret':self.client_secret,'redirect_uri':self.redirect_uri,'grant_type':'authorization_code'},timeout=30)
        if not r.ok: raise RuntimeError(f'OAuth token exchange failed: {r.status_code} {r.text[:300]}')
        t=r.json()
        if self.session_state is not None: self.session_state['_gdrive_oauth_token']=t
        self._service=None; return t
    def disconnect(self):
        if self.session_state is not None: self.session_state.pop('_gdrive_oauth_token',None)
        self._service=None
    def _credentials(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        t=self._tok()
        if not t: raise RuntimeError('Google Drive OAuth認証が未完了です。')
        creds=Credentials(token=t.get('access_token') or t.get('token'),refresh_token=t.get('refresh_token'),token_uri='https://oauth2.googleapis.com/token',client_id=self.client_id,client_secret=self.client_secret,scopes=SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            if self.session_state is not None:
                self.session_state['_gdrive_oauth_token']={'access_token':creds.token,'refresh_token':creds.refresh_token}
        if not creds.valid: raise RuntimeError('OAuthトークンが無効です。再接続してください。')
        return creds
    def _connect(self):
        if self._service is not None: return self._service
        if not self.configured(): raise RuntimeError('gdrive_oauth設定が未完了です。')
        from googleapiclient.discovery import build
        self._service=build('drive','v3',credentials=self._credentials(),cache_discovery=False); return self._service
    def status(self):
        if not self.enabled: return OAuthDriveStatus(False,False,'LOCAL',self.folder_id or None,None,'Google Drive OAuth連携OFF。')
        if not self.configured(): return OAuthDriveStatus(True,False,'OAUTH',self.folder_id or None,None,'OAuth設定が未完了です。')
        try:
            s=self._connect(); s.files().get(fileId=self.folder_id,fields='id,name,mimeType').execute(); fid=self.find_file(self.history_filename,self.folder_id)
            return OAuthDriveStatus(True,True,'OAUTH',self.folder_id,fid,'Google Drive OAuth接続済みです。')
        except Exception as e: return OAuthDriveStatus(True,False,'OAUTH',self.folder_id or None,None,f'Google Drive未接続: {e}')
    def find_file(self,name,parent_id):
        s=self._connect(); safe=name.replace("'","\\'"); q=f"name='{safe}' and '{parent_id}' in parents and trashed=false"
        fs=s.files().list(q=q,fields='files(id,name,modifiedTime,size)',pageSize=50).execute().get('files',[])
        if not fs: return None
        fs.sort(key=lambda x:x.get('modifiedTime',''),reverse=True); return fs[0]['id']
    def ensure_subfolder(self,name):
        s=self._connect(); safe=name.replace("'","\\'"); q=f"name='{safe}' and '{self.folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        fs=s.files().list(q=q,fields='files(id,name)',pageSize=20).execute().get('files',[])
        if fs: return fs[0]['id']
        return s.files().create(body={'name':name,'mimeType':'application/vnd.google-apps.folder','parents':[self.folder_id]},fields='id').execute()['id']
    def download_file(self,file_id,local_path):
        from googleapiclient.http import MediaIoBaseDownload
        r=self._connect().files().get_media(fileId=file_id); fh=io.BytesIO(); d=MediaIoBaseDownload(fh,r,chunksize=8*1024*1024); done=False
        while not done: _,done=d.next_chunk()
        p=Path(local_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(fh.getvalue()); return p
    def upload_file(self,local_path,name,parent_id,overwrite=True):
        from googleapiclient.http import MediaFileUpload
        s=self._connect(); ex=self.find_file(name,parent_id) if overwrite else None; media=MediaFileUpload(str(local_path),mimetype='application/octet-stream',resumable=True)
        if ex: return s.files().update(fileId=ex,body={'name':name},media_body=media,fields='id').execute()['id']
        return s.files().create(body={'name':name,'parents':[parent_id]},media_body=media,fields='id').execute()['id']
    def download_latest_history(self,local_path):
        fid=self.find_file(self.history_filename,self.folder_id)
        if not fid: return False
        self.download_file(fid,local_path); return True
    def backup_current_history(self,local_path,stamp=None):
        p=Path(local_path)
        if not p.exists(): return None
        bid=self.ensure_subfolder(self.backup_folder_name); stamp=stamp or time.strftime('%Y%m%d_%H%M%S')
        return self.upload_file(p,f'history_master_{stamp}.csv.gz',bid,overwrite=False)
    def upload_latest_history(self,local_path): return self.upload_file(local_path,self.history_filename,self.folder_id,True)
    def append_update_log(self,row,local_tmp):
        p=Path(local_tmp); ex=self.find_file(self.log_filename,self.folder_id)
        if ex:
            self.download_file(ex,p)
            try: old=pd.read_csv(p,encoding='cp932',low_memory=False)
            except Exception: old=pd.read_csv(p,encoding='utf-8-sig',low_memory=False)
        else: old=pd.DataFrame()
        pd.concat([old,pd.DataFrame([row])],ignore_index=True).to_csv(p,index=False,encoding='cp932')
        return self.upload_file(p,self.log_filename,self.folder_id,True)
