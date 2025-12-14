"""
Kumaş Kusur Tespiti ve Fiyatlandırma Sistemi
4-Point Kalite Standardı / Major-Minor Sınıflandırması
PDF Standardı: defect-classifications.pdf
"""

import streamlit as st
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent))

from src.detector import FabricDefectDetector
from src.quality_scorer import QualityScorer, DefectSeverity
from src.pricing import PricingCalculator

# Sayfa ayarları
st.set_page_config(page_title="Kumaş Kusur Tespiti", page_icon="🧵", layout="centered")


@st.cache_resource
def load_detector():
    model_path = "models/best.pt"
    if Path(model_path).exists():
        return FabricDefectDetector(model_path=model_path)
    return None


def main():
    st.title("🧵 Kumaş Kusur Tespiti")
    st.caption("4-Point Kalite Standardı | Major/Minor Sınıflandırması")

    detector = load_detector()
    if detector is None:
        st.error("Model bulunamadı!")
        return

    # Görsel yükleme
    uploaded = st.file_uploader("Kumaş görseli seçin", type=["jpg", "jpeg", "png"])

    if not uploaded:
        st.info("Lütfen bir görsel yükleyin")
        return

    # Görseli oku
    file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    st.image(image_rgb, caption="Yüklenen Görsel", use_container_width=True)

    # Ayarlar
    st.subheader("Ayarlar")
    col1, col2, col3 = st.columns(3)
    with col1:
        fabric_width = st.number_input("Genişlik (cm)", 10, 500, 150)
    with col2:
        fabric_length = st.number_input("Uzunluk (cm)", 10, 5000, 100)
    with col3:
        base_price = st.number_input("Fiyat (TL/m²)", 1.0, 10000.0, 100.0)

    conf_threshold = st.slider(
        "Güven Eşiği",
        min_value=0.1,
        max_value=0.9,
        value=0.25,
        step=0.05,
        help="Düşük değer: daha fazla tespit (yanlış pozitif riski). Yüksek değer: daha az ama güvenilir tespit."
    )

    fabric_area = (fabric_width * fabric_length) / 10000

    # Analiz butonu
    if st.button("🔍 Analiz Et", type="primary", use_container_width=True):

        with st.spinner("Analiz ediliyor..."):
            # Tespit
            result = detector.detect(image, fabric_width_cm=fabric_width, conf_threshold=conf_threshold)

            # Kalite puanlama
            defects = [{"class_name": d.class_name, "length_cm": d.length_cm} for d in result.defects]
            scorer = QualityScorer()
            quality = scorer.score_fabric(defects, fabric_area, fabric_width_cm=fabric_width)

            # Fiyatlandırma (puan bazlı oransal indirim)
            calculator = PricingCalculator(
                base_price_per_m2=base_price,
                discount_multiplier=0.5,  # Her 10 puan için %5
                max_discount_rate=0.70,   # Maksimum %70 indirim
            )
            pricing = calculator.calculate_price(quality)

        # Tespit sonucu görseli
        if result.annotated_image is not None:
            annotated = cv2.cvtColor(result.annotated_image, cv2.COLOR_BGR2RGB)
            st.image(annotated, caption="Tespit Sonucu", use_container_width=True)

        # Sonuçlar
        st.subheader("Sonuçlar")

        # Ana metrikler
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kusur", f"{result.total_defects} adet")
        c2.metric("Kalite", quality.grade.value)
        c3.metric("Puan", f"{quality.points_per_100m2:.1f}/100m²")
        c4.metric(
            "Yeni Fiyat",
            f"{pricing.total_price:.2f} TL",
            delta=f"-{pricing.discount_rate*100:.0f}%" if pricing.discount_rate > 0 else None,
            delta_color="inverse"
        )

        # Detaylı puanlama
        st.subheader("Puanlama Detayları")
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Majör Puan", f"{quality.major_points:.2f}")
        pc2.metric("Minör Puan", f"{quality.minor_points:.2f}")
        pc3.metric("Toplam Puan", f"{quality.total_points:.2f}")

        # Kusur detayları
        if result.total_defects > 0:
            st.write("**Kusur Listesi:**")
            defect_tr = {"Hole": "Delik", "Knot": "Düğüm", "Line": "Çizgi", "Stain": "Leke"}
            severity_tr = {DefectSeverity.MAJOR: "Majör", DefectSeverity.MINOR: "Minör"}

            for i, ds in enumerate(quality.defect_scores, 1):
                defect_name = defect_tr.get(ds.defect_class, ds.defect_class)
                severity_name = severity_tr.get(ds.severity, ds.severity.value)
                st.write(f"{i}. {defect_name} [{severity_name}]: {ds.length_cm:.1f} cm → {ds.points:.2f} puan")

            # Özet tablo
            st.write("**Kusur Özeti:**")
            for name, count in result.defect_summary.items():
                if count > 0:
                    summary_data = quality.summary.get(name, {})
                    major_count = summary_data.get("major_count", 0)
                    minor_count = summary_data.get("minor_count", 0)
                    points = summary_data.get("points", 0)
                    st.write(f"- {defect_tr.get(name, name)}: {count} adet ({major_count} majör, {minor_count} minör) → {points:.2f} puan")

        # Fiyatlandırma detayları
        st.subheader("Fiyatlandırma")
        fc1, fc2 = st.columns(2)
        with fc1:
            st.write("**Kumaş Bilgileri:**")
            st.write(f"- Genişlik: {fabric_width} cm")
            st.write(f"- Uzunluk: {fabric_length} cm")
            st.write(f"- Alan: {fabric_area:.2f} m²")
        with fc2:
            st.write("**Fiyat Hesabı:**")
            st.write(f"- Sabit Fiyat: {pricing.base_price_per_m2:.2f} TL/m²")
            st.write(f"- İndirim Oranı: %{pricing.discount_rate*100:.1f}")
            st.write(f"- İndirimli Fiyat: {pricing.adjusted_price_per_m2:.2f} TL/m²")

        # İndirim detayları
        st.write("**İndirim Hesabı:**")
        ind1, ind2, ind3 = st.columns(3)
        ind1.metric("Sabit Toplam", f"{pricing.total_base_price:.2f} TL")
        ind2.metric("İndirim", f"-{pricing.discount_amount:.2f} TL")
        ind3.metric("Yeni Fiyat", f"{pricing.total_price:.2f} TL")

        # Bilgi Fişi
        st.subheader("Bilgi Fişi")

        receipt = f"""════════════════════════════════════════════════
          KUMAŞ KALİTE ANALİZ FİŞİ
      4-Point Sistemi / Major-Minor Standardı
════════════════════════════════════════════════
Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}

KUMAŞ BİLGİLERİ
  Genişlik    : {fabric_width} cm
  Uzunluk     : {fabric_length} cm
  Alan        : {fabric_area:.2f} m²

KUSUR TESPİTİ
  Toplam Kusur: {result.total_defects} adet
  Majör Puan  : {quality.major_points:.2f}
  Minör Puan  : {quality.minor_points:.2f}
  Toplam Puan : {quality.total_points:.2f}

KALİTE DEĞERLENDİRMESİ
  100m² Puan  : {quality.points_per_100m2:.2f}
  Kalite Sınıfı: {quality.grade.value}
  Durum       : {quality.grade_description}

FİYATLANDIRMA (Puan Bazlı İndirim)
  Sabit Fiyat : {pricing.base_price_per_m2:.2f} TL/m²
  İndirim     : %{pricing.discount_rate*100:.1f}
  Yeni Fiyat  : {pricing.adjusted_price_per_m2:.2f} TL/m²
  ────────────────────────────────────────────
  Sabit Toplam: {pricing.total_base_price:.2f} TL
  İndirim     : -{pricing.discount_amount:.2f} TL
  ════════════════════════════════════════════
  YENİ FİYAT  : {pricing.total_price:.2f} TL
════════════════════════════════════════════════
Standart: 4-Point System (ASTM D5430)
Major: 1 puan / 9 inç (23 cm)
Minor: 0.25 puan / 9 inç (23 cm)
İndirim: Her 10 puan için %5 (maks %70)
Kabul Sınırı: 40 puan/100m²
════════════════════════════════════════════════"""

        st.code(receipt)

        st.download_button(
            "📥 Fişi İndir",
            receipt,
            f"kumas_fis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
