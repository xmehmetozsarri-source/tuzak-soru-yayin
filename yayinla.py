"""Tuzak Soru otomatik yayin: kuyruk/<id>/ klasorlerindeki videolari
YouTube'a (zamanlanmis) yukler, TikTok'a yayin saatinde taslak (inbox) gonderir."""
import os, json, glob, datetime as dt, requests

NOW = dt.datetime.now(dt.timezone.utc)

def log(*a): print(*a, flush=True)

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

def save(p, d):
    with open(p, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)

# ---------------- YouTube
def yt_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=60)
    r.raise_for_status(); return r.json()["access_token"]

def yt_upload(folder, meta, pub):
    tok = yt_token(); y = meta["youtube"]
    body = {"snippet": {"title": y["title"][:100], "description": y.get("description", ""),
                        "tags": y.get("tags", []), "categoryId": "27", "defaultLanguage": "tr"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}
    if meta.get("test"):
        pass  # deneme: gizli kalir
    elif pub > NOW + dt.timedelta(minutes=20):
        body["status"]["publishAt"] = pub.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        body["status"]["privacyStatus"] = "public"
    video = os.path.join(folder, "video.mp4"); size = os.path.getsize(video)
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      data=json.dumps(body), timeout=60)
    r.raise_for_status()
    with open(video, "rb") as f:
        u = requests.put(r.headers["Location"], headers={"Content-Type": "video/mp4"}, data=f, timeout=600)
    u.raise_for_status(); vid = u.json()["id"]
    log("YouTube yuklendi:", vid); return vid

# ---------------- TikTok (inbox / taslak)
def tt_token():
    r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": os.environ["TT_CLIENT_KEY"], "client_secret": os.environ["TT_CLIENT_SECRET"],
        "grant_type": "refresh_token", "refresh_token": os.environ["TT_REFRESH_TOKEN"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=60)
    r.raise_for_status(); j = r.json()
    if "access_token" not in j: raise RuntimeError(f"TikTok token hatasi: {j}")
    return j["access_token"]

def tt_inbox(folder):
    tok = tt_token(); video = os.path.join(folder, "video.mp4"); size = os.path.getsize(video)
    r = requests.post("https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"},
                      json={"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}},
                      timeout=60)
    j = r.json()
    if r.status_code != 200 or j.get("error", {}).get("code") not in ("ok", None):
        raise RuntimeError(f"TikTok init hatasi: {j}")
    url = j["data"]["upload_url"]
    with open(video, "rb") as f:
        u = requests.put(url, headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size-1}/{size}"}, data=f, timeout=600)
    u.raise_for_status(); log("TikTok taslak gonderildi:", j["data"].get("publish_id")); return j["data"].get("publish_id")

def main():
    have_yt = all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    have_tt = all(os.environ.get(k) for k in ("TT_CLIENT_KEY", "TT_CLIENT_SECRET", "TT_REFRESH_TOKEN"))
    for mp in sorted(glob.glob("kuyruk/*/meta.json")):
        folder = os.path.dirname(mp); meta = load(mp); st = meta.setdefault("durum", {})
        pub = dt.datetime.fromisoformat(meta["yayin_zamani"]).astimezone(dt.timezone.utc)
        if have_yt and "youtube" in meta and not st.get("youtube"):
            try: st["youtube"] = yt_upload(folder, meta, pub); save(mp, meta)
            except Exception as e: log("YouTube HATA", folder, e); st["youtube_hata"] = str(e)[:300]; save(mp, meta)
        if have_tt and meta.get("tiktok", True) and not st.get("tiktok") and NOW >= pub - dt.timedelta(minutes=10):
            try: st["tiktok"] = tt_inbox(folder) or "ok"; save(mp, meta)
            except Exception as e: log("TikTok HATA", folder, e); st["tiktok_hata"] = str(e)[:300]; save(mp, meta)

if __name__ == "__main__":
    main()
