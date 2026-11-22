"""Tuzak Soru YouTube kanal istatistiklerini istatistik/ klasorune yazar.
Analytics izni varsa izlenme suresi / tutma oranlarini da ekler."""
import os, json, datetime as dt, requests
from yayinla import yt_token
tok = yt_token(); H = {"Authorization": f"Bearer {tok}"}; B = "https://www.googleapis.com/youtube/v3/"
ch = requests.get(B + "channels", params={"part": "snippet,statistics,contentDetails", "mine": "true"}, headers=H, timeout=60).json()["items"][0]
up = ch["contentDetails"]["relatedPlaylists"]["uploads"]; ids, tokn = [], None
while True:
    r = requests.get(B + "playlistItems", params={"part": "contentDetails", "playlistId": up, "maxResults": 50, "pageToken": tokn}, headers=H, timeout=60).json()
    ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]; tokn = r.get("nextPageToken")
    if not tokn or len(ids) >= 200: break
vids = []
for k in range(0, len(ids), 50):
    r = requests.get(B + "videos", params={"part": "snippet,statistics,contentDetails,status", "id": ",".join(ids[k:k+50])}, headers=H, timeout=60).json()
    for v in r.get("items", []):
        s = v.get("statistics", {})
        vids.append({"id": v["id"], "baslik": v["snippet"]["title"], "yayin": v["snippet"]["publishedAt"],
                     "durum": v["status"]["privacyStatus"], "sure": v["contentDetails"]["duration"],
                     "izlenme": int(s.get("viewCount", 0)), "begeni": int(s.get("likeCount", 0)), "yorum": int(s.get("commentCount", 0))})
# --- YouTube Analytics (izin varsa)
analytics = None
try:
    today = dt.date.today(); start = (today - dt.timedelta(days=90)).isoformat()
    r = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers=H, timeout=60, params={
        "ids": "channel==MINE", "startDate": start, "endDate": today.isoformat(), "dimensions": "video",
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,shares",
        "sort": "-views", "maxResults": 200})
    if r.status_code == 200:
        j = r.json(); cols = [c["name"] for c in j.get("columnHeaders", [])]
        analytics = {row[0]: dict(zip(cols[1:], row[1:])) for row in j.get("rows", [])}
        for v in vids:
            if v["id"] in analytics: v["analytics"] = analytics[v["id"]]
    else:
        print("Analytics izni yok veya hata:", r.status_code)
except Exception as e:
    print("Analytics hata:", e)
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
out = {"zaman": now, "kanal": ch["snippet"]["title"], "abone": int(ch["statistics"].get("subscriberCount", 0)),
       "toplam_izlenme": int(ch["statistics"].get("viewCount", 0)), "video_sayisi": int(ch["statistics"].get("videoCount", 0)),
       "analytics_var": analytics is not None, "videolar": vids}
os.makedirs("istatistik", exist_ok=True)
json.dump(out, open("istatistik/son.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open("istatistik/gecmis.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps({"zaman": now, "abone": out["abone"], "toplam_izlenme": out["toplam_izlenme"],
                        "videolar": {v["id"]: [v["izlenme"], v["begeni"], v["yorum"]] for v in vids}}, ensure_ascii=False) + "\n")
print(out["kanal"], out["abone"], "abone,", len(vids), "video, analytics:", out["analytics_var"])
# guncel: analytics izni eklendi
# analytics api acildi
