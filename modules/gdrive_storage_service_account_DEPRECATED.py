
from __future__ import annotations
import io, json, os, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pandas as pd

@dataclass
class DriveStatus:
    enabled: bool
    connected: bool
    mode: str
    folder_id: str | None
    history_file_id: str | None
    message: str

class GoogleDriveStorage:
    def __init__(self,secrets=None):
        self.cfg={}
        if secrets is not None:
            try:self.cfg=dict(secrets.get("gdrive",{}))
            except Exception:self.cfg={}
        self.enabled=bool(self.cfg.get("enabled",False))
        self.folder_id=str(self.cfg.get("folder_id","") or "").strip()
        self.history_filename=str(self.cfg.get("history_filename","history_master.csv.gz"))
        self.backup_folder_name=str(self.cfg.get("backup_folder_name","backup"))
        self.log_filename=str(self.cfg.get("log_filename","update_log.csv"))
        self._service=None
    def _credentials_info(self):
        raw=self.cfg.get("service_account_json") or os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
        if not raw:return None
        if isinstance(raw,dict):return raw
        return json.loads(str(raw))
    def _connect(self):
        if self._service is not None:return self._service
        if not self.enabled:raise RuntimeError("Google Drive連携OFF")
        if not self.folder_id:raise RuntimeError("gdrive.folder_id 未設定")
        info=self._credentials_info()
        if not info:raise RuntimeError("サービスアカウントJSON未設定")
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds=Credentials.from_service_account_info(info,scopes=["https://www.googleapis.com/auth/drive"])
        self._service=build("drive","v3",credentials=creds,cache_discovery=False)
        return self._service
    def status(self):
        if not self.enabled:return DriveStatus(False,False,"LOCAL",self.folder_id or None,None,"Google Drive連携OFF")
        try:
            s=self._connect(); s.files().get(fileId=self.folder_id,fields="id,name,mimeType").execute()
            fid=self.find_file(self.history_filename,self.folder_id)
            return DriveStatus(True,True,"GDRIVE",self.folder_id,fid,"Google Drive接続済み")
        except Exception as e:
            return DriveStatus(True,False,"GDRIVE",self.folder_id or None,None,f"接続失敗: {e}")
    def find_file(self,name,parent_id):
        s=self._connect(); safe=name.replace("'","\'")
        q=f"name='{safe}' and '{parent_id}' in parents and trashed=false"
        fs=s.files().list(q=q,fields="files(id,name,modifiedTime,size)",pageSize=20).execute().get("files",[])
        if not fs:return None
        fs.sort(key=lambda x:x.get("modifiedTime",""),reverse=True); return fs[0]["id"]
    def ensure_subfolder(self,name):
        s=self._connect(); safe=name.replace("'","\'")
        q=f"name='{safe}' and '{self.folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        fs=s.files().list(q=q,fields="files(id,name)",pageSize=20).execute().get("files",[])
        if fs:return fs[0]["id"]
        return s.files().create(body={"name":name,"mimeType":"application/vnd.google-apps.folder","parents":[self.folder_id]},fields="id").execute()["id"]
    def download_file(self,file_id,local_path):
        from googleapiclient.http import MediaIoBaseDownload
        s=self._connect(); req=s.files().get_media(fileId=file_id); fh=io.BytesIO(); dl=MediaIoBaseDownload(fh,req,chunksize=8*1024*1024); done=False
        while not done: _,done=dl.next_chunk()
        p=Path(local_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(fh.getvalue()); return p
    def upload_file(self,local_path,name,parent_id,overwrite=True):
        from googleapiclient.http import MediaFileUpload
        s=self._connect(); existing=self.find_file(name,parent_id) if overwrite else None
        media=MediaFileUpload(str(local_path),mimetype="application/octet-stream",resumable=True)
        if existing:
            return s.files().update(fileId=existing,body={"name":name},media_body=media,fields="id").execute()["id"]
        return s.files().create(body={"name":name,"parents":[parent_id]},media_body=media,fields="id").execute()["id"]
    def download_latest_history(self,local_path):
        fid=self.find_file(self.history_filename,self.folder_id)
        if not fid:return False
        self.download_file(fid,local_path); return True
    def backup_current_history(self,local_path,stamp=None):
        p=Path(local_path)
        if not p.exists():return None
        bid=self.ensure_subfolder(self.backup_folder_name); stamp=stamp or time.strftime("%Y%m%d_%H%M%S")
        return self.upload_file(p,f"history_master_{stamp}.csv.gz",bid,overwrite=False)
    def upload_latest_history(self,local_path):
        return self.upload_file(local_path,self.history_filename,self.folder_id,overwrite=True)
    def append_update_log(self,row,local_tmp):
        p=Path(local_tmp); fid=self.find_file(self.log_filename,self.folder_id)
        if fid:
            self.download_file(fid,p)
            try:old=pd.read_csv(p,encoding="cp932",low_memory=False)
            except Exception:old=pd.read_csv(p,encoding="utf-8-sig",low_memory=False)
        else:old=pd.DataFrame()
        new=pd.concat([old,pd.DataFrame([row])],ignore_index=True); new.to_csv(p,index=False,encoding="cp932")
        return self.upload_file(p,self.log_filename,self.folder_id,overwrite=True)
