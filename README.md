# MineSentinel AIoT Platform (v1.0)

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



### Anomaly Detection

MineSentinel uses Isolation Forest for unsupervised anomaly detection.

The initial `contamination` parameter was set to `0.20`, based on the
observed proportion of higher-risk samples in the initial synthetic
dataset.

> This is an initial calibration value and does not represent the
> real-world anomaly rate in mining environments.

For the full rationale and EDA analysis, see
[Isolation Forest Contamination Decision](docs/decisions/005-isolation-forest-contamination.md).

## 🛡 Üç Katmanlı Güvenlik ve Karar Mekanizması

MineSentinel, tek bir hata noktasına (Single Point of Failure) bağımlı kalmamak adına sensör verilerini 3 tamamlayıcı katmanda işler:

### 1. Kural Tabanlı Risk Motoru (`RiskEngine`)
* **Türü:** Deterministik & Ağırlıklı Matematiksel Model
* **Görevi:** Sensörlerden gelen gaz, ivme ve maruziyet süresi değerlerini normalleştirerek 0-100 arasında net bir **Risk Skoru** üretir.
* **Neden Gerekli?** Önceden tanımlanmış net fiziksel sınırları (ör. anlık yüksek gaz veya sert darbe) gecikmesiz ve kesin kurallarla doğrudan tespit eder.

### 2. Denetimsiz Anomali Tespiti (`Isolation Forest`)
* **Türü:** Unsupervised Machine Learning
* **Görevi:** Etiketlere ihtiyaç duymadan, çok boyutlu sensör uzayında normal davranış kümesinden sapan aykırı noktaları izole eder.
* **Neden Gerekli?** Daha önce tanımlanmamış kriz senaryolarını, beklenmeyen sensör dalgalanmalarını ve sıfır-gün (zero-day) anomalilerini yakalar.

### 3. Denetimli Risk Sınıflandırma (`Supervised Classifier`)
* **Türü:** Supervised Machine Learning (Random Forest)
* **Görevi:** Geçmiş etiketli veri modellerini öğrenerek durumun ciddiyetini (`LOW`, `MEDIUM`, `CRITICAL`) sınıflandırır ve olasılıksal güven skoru üretir.
* **Neden Gerekli?** Tehlikenin sadece varlığını değil, hangi seviyede olduğunu ve olasılık dağılımını (ör. %92 CRITICAL) belirleyerek doğru müdahale kararının verilmesini sağlar.