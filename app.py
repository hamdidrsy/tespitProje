"""
Kumaş Kusur Tespiti ve Fiyatlandırma Sistemi
"""

import streamlit as st
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent))

from src.detector import FabricDefectDetector
from src.quality_scorer import QualityScorer
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
        base_price = st.number_input("Fiyat (TL/m²)", 1.0, 1000.0, 25.0)

    fabric_area = (fabric_width * fabric_length) / 10000

    # Analiz butonu
    if st.button("🔍 Analiz Et", type="primary", use_container_width=True):

        with st.spinner("Analiz ediliyor..."):
            # Tespit
            result = detector.detect(image, fabric_width_cm=fabric_width)

            # Kalite puanlama
            defects = [{"class_name": d.class_name, "length_cm": d.length_cm} for d in result.defects]
            scorer = QualityScorer()
            quality = scorer.score_fabric(defects, fabric_area)

            # Fiyatlandırma
            calculator = PricingCalculator(base_price_per_m2=base_price)
            pricing = calculator.calculate_price(quality)

        # Tespit sonucu görseli
        if result.annotated_image is not None:
            annotated = cv2.cvtColor(result.annotated_image, cv2.COLOR_BGR2RGB)
            st.image(annotated, caption="Tespit Sonucu", use_container_width=True)

        # Sonuçlar
        st.subheader("Sonuçlar")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kusur", f"{result.total_defects} adet")
        c2.metric("Kalite", quality.grade.value)
        c3.metric("Puan", f"{quality.points_per_100m2:.1f}")
        c4.metric("Fiyat", f"{pricing.total_adjusted_price:.2f} TL")

        # Kusur detayları
        if result.total_defects > 0:
            st.write("**Kusurlar:**")
            defect_tr = {"Hole": "Delik", "Knot": "Düğüm", "Line": "Çizgi", "Stain": "Leke"}
            for name, count in result.defect_summary.items():
                if count > 0:
                    st.write(f"- {defect_tr.get(name, name)}: {count}")

        # Bilgi Fişi
        st.subheader("Bilgi Fişi")

        receipt = f"""════════════════════════════════════
       KUMAŞ KALİTE ANALİZ FİŞİ
════════════════════════════════════
Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}

KUMAŞ BİLGİLERİ
  Genişlik    : {fabric_width} cm
  Uzunluk     : {fabric_length} cm
  Alan        : {fabric_area:.2f} m²

KUSUR TESPİTİ
  Toplam      : {result.total_defects} adet

KALİTE
  Puan        : {quality.points_per_100m2:.1f} / 100m²
  Sınıf       : {quality.grade.value}

FİYAT
  Birim       : {pricing.base_price_per_m2:.2f} TL/m²
  İndirim     : %{pricing.discount_percentage:.0f}
  TOPLAM      : {pricing.total_adjusted_price:.2f} TL
════════════════════════════════════"""

        st.code(receipt)

        st.download_button(
            "📥 Fişi İndir",
            receipt,
            f"kumas_fis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
