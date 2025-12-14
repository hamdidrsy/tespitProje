"""
Kumaş Kusur Tespiti - Fiyatlandırma Modülü
Puan Bazlı Oransal İndirim Sistemi

Formül:
- İndirim Oranı = Puan/100m² × Çarpan (maks %70)
- Yeni Fiyat = Sabit Fiyat - (Sabit Fiyat × İndirim Oranı)
"""

from typing import Dict, Optional
from dataclasses import dataclass
from .quality_scorer import QualityGrade, QualityReport


@dataclass
class PricingResult:
    """Fiyatlandırma sonucu"""
    base_price_per_m2: float          # Sabit birim fiyat (TL/m²)
    adjusted_price_per_m2: float      # İndirimli birim fiyat (TL/m²)
    total_base_price: float           # Sabit toplam fiyat
    total_price: float                # İndirimli toplam fiyat
    discount_rate: float              # İndirim oranı (0-1)
    discount_amount: float            # Toplam indirim tutarı (TL)
    fabric_area_m2: float             # Kumaş alanı
    quality_grade: QualityGrade       # Kalite sınıfı
    points_per_100m2: float           # 100m² başına puan
    total_points: float               # Toplam puan
    major_points: float               # Major puanlar
    minor_points: float               # Minor puanlar
    currency: str                     # Para birimi


class PricingCalculator:
    """
    Puan Bazlı Oransal İndirim Hesaplayıcı

    Formül:
    - İndirim Oranı = (Puan/100m²) × Çarpan
    - Maksimum indirim oranı sınırlaması var
    - Yeni Fiyat = Sabit Fiyat × (1 - İndirim Oranı)

    Örnek (çarpan=0.5, maks=%70):
    - 10 puan/100m² → %5 indirim
    - 40 puan/100m² → %20 indirim
    - 60 puan/100m² → %30 indirim
    - 140+ puan/100m² → %70 indirim (maksimum)
    """

    def __init__(
        self,
        base_price_per_m2: float = 100.0,
        discount_multiplier: float = 0.5,
        max_discount_rate: float = 0.70,
        currency: str = "TL",
    ):
        """
        Args:
            base_price_per_m2: Sabit birim fiyat (TL/m²)
            discount_multiplier: Puan çarpanı (0.5 = her 10 puan için %5)
            max_discount_rate: Maksimum indirim oranı (0.70 = %70)
            currency: Para birimi
        """
        self.base_price_per_m2 = base_price_per_m2
        self.discount_multiplier = discount_multiplier
        self.max_discount_rate = max_discount_rate
        self.currency = currency

    def calculate_discount_rate(self, points_per_100m2: float) -> float:
        """
        Puana göre indirim oranını hesapla.

        Formül: İndirim Oranı = (Puan/100m²) × Çarpan / 100
        Örnek: 40 puan × 0.5 / 100 = 0.20 = %20

        Args:
            points_per_100m2: 100m² başına puan

        Returns:
            İndirim oranı (0-max_discount_rate arası)
        """
        # Ham indirim oranı
        raw_rate = (points_per_100m2 * self.discount_multiplier) / 100

        # Maksimum sınırla
        return min(raw_rate, self.max_discount_rate)

    def calculate_price(
        self,
        quality_report: QualityReport,
        custom_price_per_m2: Optional[float] = None,
    ) -> PricingResult:
        """
        Kalite raporuna göre fiyat hesapla.

        Args:
            quality_report: Kalite raporu
            custom_price_per_m2: Özel sabit fiyat (opsiyonel)

        Returns:
            PricingResult: Fiyatlandırma sonucu
        """
        base_price = custom_price_per_m2 or self.base_price_per_m2
        fabric_area = quality_report.fabric_area_m2
        points_per_100m2 = quality_report.points_per_100m2

        # İndirim oranını hesapla
        discount_rate = self.calculate_discount_rate(points_per_100m2)

        # İndirimli birim fiyat
        adjusted_price = base_price * (1 - discount_rate)

        # Toplam fiyatlar
        total_base_price = base_price * fabric_area
        total_price = adjusted_price * fabric_area

        # İndirim tutarı
        discount_amount = total_base_price - total_price

        return PricingResult(
            base_price_per_m2=round(base_price, 2),
            adjusted_price_per_m2=round(adjusted_price, 2),
            total_base_price=round(total_base_price, 2),
            total_price=round(total_price, 2),
            discount_rate=round(discount_rate, 4),
            discount_amount=round(discount_amount, 2),
            fabric_area_m2=fabric_area,
            quality_grade=quality_report.grade,
            points_per_100m2=quality_report.points_per_100m2,
            total_points=quality_report.total_points,
            major_points=quality_report.major_points,
            minor_points=quality_report.minor_points,
            currency=self.currency,
        )

    def format_price(self, amount: float) -> str:
        """Fiyatı formatla"""
        return f"{amount:,.2f} {self.currency}"

    def format_report(self, result: PricingResult) -> str:
        """Fiyatlandırma raporunu formatla"""
        discount_percent = result.discount_rate * 100
        lines = [
            "=" * 50,
            "FİYATLANDIRMA RAPORU",
            "Puan Bazlı Oransal İndirim Sistemi",
            "=" * 50,
            f"Kumaş Alanı: {result.fabric_area_m2:.2f} m²",
            f"Kalite Sınıfı: {result.quality_grade.value}",
            f"100m² Başına Puan: {result.points_per_100m2:.2f}",
            "-" * 50,
            "FİYAT HESABI:",
            f"  Sabit Fiyat: {self.format_price(result.base_price_per_m2)}/m²",
            f"  İndirim Oranı: %{discount_percent:.1f}",
            f"  İndirimli Fiyat: {self.format_price(result.adjusted_price_per_m2)}/m²",
            "-" * 50,
            f"  Sabit Toplam: {self.format_price(result.total_base_price)}",
            f"  İndirim Tutarı: -{self.format_price(result.discount_amount)}",
            f"  ────────────────────────────────────────────",
            f"  YENİ FİYAT: {self.format_price(result.total_price)}",
            "=" * 50,
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    from .quality_scorer import QualityScorer

    # Test
    scorer = QualityScorer()
    calculator = PricingCalculator(
        base_price_per_m2=100.0,
        discount_multiplier=0.5,
        max_discount_rate=0.70,
    )

    # Örnek kusurlar
    test_defects = [
        {"class_name": "Hole", "length_cm": 5.0},
        {"class_name": "Stain", "length_cm": 12.0},
        {"class_name": "Line", "length_cm": 30.0},
    ]

    # Kalite raporu
    quality_report = scorer.score_fabric(test_defects, fabric_area_m2=10.0)
    print(scorer.format_report(quality_report))

    # Fiyat hesapla
    pricing_result = calculator.calculate_price(quality_report)
    print("\n")
    print(calculator.format_report(pricing_result))
