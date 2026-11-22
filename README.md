# Tuzak Soru – otomatik yayın

Her video `kuyruk/<tarih_konu>/` klasöründe durur: `video.mp4` + `meta.json`.
GitHub Actions her 15 dakikada bir çalışır:
- **YouTube:** video yüklenir ve `yayin_zamani`'na zamanlanır.
- **TikTok:** yayın saatinde video TikTok'a **taslak** olarak gönderilir (uygulamadan "Paylaş").
- **Instagram:** elle paylaşılır.

Durum `meta.json` içindeki `durum` alanına yazılır.
