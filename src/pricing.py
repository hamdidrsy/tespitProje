"""
Kumaş Kusur Tespiti - Fiyatlandırma Modülü
Kalite sınıfına göre fiyat hesaplama
"""

from typing import Dict, Optional
from dataclasses import dataclass
from .quality_scorer import QualityGrade, QualityReport


@dataclass
class PricingResult:
    """Fiyatlandırma sonucu"""
    base_price_per_m2: float
    adjusted_price_per_m2: float
    total_base_price: float
    total_adjusted_price: float
    discount_percentage: float
    discount_amount: float
    fabric_area_m2: float
    quality_grade: QualityGrade
    currency: str


class PricingCalculator:
    """Kalite bazlı fiyatlandırma hesaplayıcı"""

    # Varsayılan kalite çarpanları
    DEFAULT_GRADE_MULTIPLIERS = {
        QualityGrade.A: 1.0,      # %100 - Tam fiyat
        QualityGrade.B: 0.85,     # %85
        QualityGrade.C: 0.70,     # %70
        QualityGrade.REJECT: 0.0,  # %0 veya hurda fiyatı
    }

    def __init__(
        self,
        base_price_per_m2: float = 100.0,
        currency: str = "TL",
        grade_multipliers: Optional[Dict[QualityGrade, float]] = None,
        reject_price_per_m2: float = 0.0,
    ):
        """
        Args:
            base_price_per_m2: Baz fiyat (birinci kalite için TL/m²)
            currency: Para birimi
            grade_multipliers: Kalite sınıfı çarpanları
            reject_price_per_m2: Ret edilen kumaş için hurda fiyatı
        """
        self.base_price_per_m2 = base_price_per_m2
        self.currency = currency
        self.grade_multipliers = grade_multipliers or self.DEFAULT_GRADE_MULTIPLIERS.copy()
        self.reject_price_per_m2 = reject_price_per_m2

    def calculate_price(
        self,
        quality_report: QualityReport,
        custom_base_price: Optional[float] = None,
    ) -> PricingResult:
        """
        Kalite raporuna göre fiyat hesapla.

        Args:
            quality_report: Kalite raporu
            custom_base_price: Özel baz fiyat (opsiyonel)

        Returns:
            PricingResult: Fiyatlandırma sonucu
        """
        base_price = custom_base_price or self.base_price_per_m2
        fabric_area = quality_report.fabric_area_m2
        grade = quality_report.grade

        # Kalite çarpanı
        multiplier = self.grade_multipliers.get(grade, 0.0)

        # Ret durumunda hurda fiyatı uygula
        if grade == QualityGrade.REJECT:
            adjusted_price_per_m2 = self.reject_price_per_m2
        else:
            adjusted_price_per_m2 = base_price * multiplier

        # Toplam fiyatlar
        total_base_price = base_price * fabric_area
        total_adjusted_price = adjusted_price_per_m2 * fabric_area

        # İndirim
        discount_percentage = (1 - multiplier) * 100
        discount_amount = total_base_price - total_adjusted_price

        return PricingResult(
            base_price_per_m2=base_price,
            adjusted_price_per_m2=round(adjusted_price_per_m2, 2),
            total_base_price=round(total_base_price, 2),
            total_adjusted_price=round(total_adjusted_price, 2),
            discount_percentage=round(discount_percentage, 1),
            discount_amount=round(discount_amount, 2),
            fabric_area_m2=fabric_area,
            quality_grade=grade,
            currency=self.currency,
        )

    def calculate_price_simple(
        self,
        grade: QualityGrade,
        fabric_area_m2: float,
        custom_base_price: Optional[float] = None,
    ) -> PricingResult:
        """
        Basit fiyat hesaplama (sadece kalite sınıfı ve alan ile).

        Args:
            grade: Kalite sınıfı
            fabric_area_m2: Kumaş alanı
            custom_base_price: Özel baz fiyat

        Returns:
            PricingResult: Fiyatlandırma sonucu
        """
        base_price = custom_base_price or self.base_price_per_m2
        multiplier = self.grade_multipliers.get(grade, 0.0)

        if grade == QualityGrade.REJECT:
            adjusted_price_per_m2 = self.reject_price_per_m2
        else:
            adjusted_price_per_m2 = base_price * multiplier

        total_base_price = base_price * fabric_area_m2
        total_adjusted_price = adjusted_price_per_m2 * fabric_area_m2
        discount_percentage = (1 - multiplier) * 100
        discount_amount = total_base_price - total_adjusted_price

        return PricingResult(
            base_price_per_m2=base_price,
            adjusted_price_per_m2=round(adjusted_price_per_m2, 2),
            total_base_price=round(total_base_price, 2),
            total_adjusted_price=round(total_adjusted_price, 2),
            discount_percentage=round(discount_percentage, 1),
            discount_amount=round(discount_amount, 2),
            fabric_area_m2=fabric_area_m2,
            quality_grade=grade,
            currency=self.currency,
        )

    def format_price(self, amount: float) -> str:
        """Fiyatı formatla"""
        return f"{amount:,.2f} {self.currency}"

    def format_report(self, result: PricingResult) -> str:
        """Fiyatlandırma raporunu formatla"""
        lines = [
            "=" * 50,
            "FİYATLANDIRMA RAPORU",
            "=" * 50,
            f"Kumaş Alanı: {result.fabric_area_m2:.2f} m²",
            f"Kalite Sınıfı: {result.quality_grade.value}",
            "-" * 50,
            f"Baz Fiyat: {self.format_price(result.base_price_per_m2)}/m²",
            f"Ayarlı Fiyat: {self.format_price(result.adjusted_price_per_m2)}/m²",
            f"İndirim: %{result.discount_percentage:.1f}",
            "-" * 50,
            f"Toplam Baz Fiyat: {self.format_price(result.total_base_price)}",
            f"İndirim Tutarı: -{self.format_price(result.discount_amount)}",
            "-" * 50,
            f"ÖDENECEK TUTAR: {self.format_price(result.total_adjusted_price)}",
            "=" * 50,
        ]
        return "\n".join(lines)

    def get_grade_info(self) -> Dict[str, dict]:
        """Tüm kalite sınıfları için bilgi döndür"""
        info = {}
        for grade in QualityGrade:
            multiplier = self.grade_multipliers.get(grade, 0.0)
            info[grade.value] = {
                "multiplier": multiplier,
                "discount_percentage": (1 - multiplier) * 100,
                "price_per_m2": self.base_price_per_m2 * multiplier,
            }
        return info


if __name__ == "__main__":
    from .quality_scorer import QualityScorer

    # Test
    scorer = QualityScorer()
    calculator = PricingCalculator(base_price_per_m2=150.0)

    # Örnek kusurlar
    test_defects = [
        {"class_name": "Hole", "length_cm": 5.0},
        {"class_name": "Stain", "length_cm": 12.0},
    ]

    # Kalite raporu
    quality_report = scorer.score_fabric(test_defects, fabric_area_m2=50.0)
    print(scorer.format_report(quality_report))

    # Fiyat hesapla
    pricing_result = calculator.calculate_price(quality_report)
    print("\n")
    print(calculator.format_report(pricing_result))
