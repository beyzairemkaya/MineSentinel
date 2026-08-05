# 🛡️ MineSentinel AIoT Platform (v1.0)

**MineSentinel**, yeraltı madenciliğinde çalışan işçilerin güvenliğini artırmak amacıyla geliştirilmiş Edge AI ve IoT tabanlı bir güvenlik platformudur. 

Sistem; ortamdaki zehirli/yanıcı gaz seviyelerini ve işçinin ivme/hareketsizlik durumlarını eş zamanlı analiz ederek deterministik bir **Risk Skoru (0-100)** üreder ve kriz anında yapay zeka destekli otomatik acil durum raporları oluşturur.

---

##  Sistem Mimarisi

- **Edge Device (Firmware):** ESP32 + MPU6050 (İvme/Düşme) + MQ-2 (Gaz)
- **AI & Risk Engine (Backend):** Python, Isolation Forest (Anomali Tespiti), Featherless AI (LLM Raporlama)
- **Command Center (Frontend):** Streamlit Canlı Kontrol Paneli

---

##  Proje Dizin Yapısı

```text
MineSentinel/
├── backend/       # Risk motoru, anomali tespiti ve LLM modülleri
├── dashboard/     # Streamlit arayüzü
├── firmware/      # ESP32 C++ kodları
├── scripts/       # Sentetik veri üretme araçları
├── data/          # Sensör veritabanı (CSV)
├── docs/          # Mimari ve donanım dokümantasyonu
└── tests/         # Test senaryoları