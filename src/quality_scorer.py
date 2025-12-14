"""
Kumaş Kusur Tespiti - Kalite Puanlama Modülü
4-Point Uluslararası Kalite Standardı
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class QualityGrade(Enum):
    """Kalite sınıfları"""
    A = "A"  # Birinci kalite
    B = "B"  # İkinci kalite
    C = "C"  # Üçüncü kalite
    REJECT = "Ret"  # Kabul edilemez


@dataclass
class DefectScore:
    """Kusur puanı bilgisi"""
    defect_class: str
    length_cm: float
    points: int
    description: str


@dataclass
class QualityReport:
    """Kalite raporu"""
    total_points: int
    points_per_100m2: float
    grade: QualityGrade
    grade_description: str
    defect_scores: List[DefectScore]
    summary: Dict[str, int]
    fabric_area_m2: float


class QualityScorer:
    """4-Point Kalite Puanlama Sistemi"""

    # 4-Point System kuralları (kusur uzunluğuna göre puan)
    POINT_RULES = [
        (7.5, 1),   # 0-7.5 cm: 1 puan
        (15.0, 2),  # 7.5-15 cm: 2 puan
        (23.0, 3),  # 15-23 cm: 3 puan
        (float('inf'), 4),  # >23 cm: 4 puan
    ]

    # Kalite sınıfı eşikleri (100 m² başına puan)
    GRADE_THRESHOLDS = {
        QualityGrade.A: (0, 20),      # 0-20 puan: A sınıfı
        QualityGrade.B: (21, 40),     # 21-40 puan: B sınıfı
        QualityGrade.C: (41, 60),     # 41-60 puan: C sınıfı
        QualityGrade.REJECT: (61, float('inf')),  # >60 puan: Ret
    }

    GRADE_DESCRIPTIONS = {
        QualityGrade.A: "Birinci Kalite - Mükemmel",
        QualityGrade.B: "İkinci Kalite - İyi",
        QualityGrade.C: "Üçüncü Kalite - Kabul Edilebilir",
        QualityGrade.REJECT: "Ret - Kabul Edilemez",
    }

    def __init__(self, max_points_per_100m2: int = 40):
        """
        Args:
            max_points_per_100m2: 100 m² başına maksimum kabul edilebilir puan
        """
        self.max_points_per_100m2 = max_points_per_100m2

    def calculate_defect_points(self, length_cm: float) -> Tuple[int, str]:
        """
        Kusur uzunluğuna göre puan hesapla.

        Args:
            length_cm: Kusur uzunluğu (cm)

        Returns:
            (puan, açıklama) tuple
        """
        for threshold, points in self.POINT_RULES:
            if length_cm <= threshold:
                if points == 1:
                    desc = f"0-7.5 cm arası ({length_cm:.1f} cm)"
                elif points == 2:
                    desc = f"7.5-15 cm arası ({length_cm:.1f} cm)"
                elif points == 3:
                    desc = f"15-23 cm arası ({length_cm:.1f} cm)"
                else:
                    desc = f"23 cm üzeri ({length_cm:.1f} cm)"
                return points, desc

        return 4, f"23 cm üzeri ({length_cm:.1f} cm)"

    def calculate_grade(self, points_per_100m2: float) -> QualityGrade:
        """
        Puana göre kalite sınıfı belirle.

        Args:
            points_per_100m2: 100 m² başına puan

        Returns:
            QualityGrade: Kalite sınıfı
        """
        for grade, (min_pts, max_pts) in self.GRADE_THRESHOLDS.items():
            if min_pts <= points_per_100m2 <= max_pts:
                return grade

        return QualityGrade.REJECT

    def score_fabric(
        self,
        defects: List[dict],
        fabric_area_m2: float = 1.0,
    ) -> QualityReport:
        """
        Kumaş kalitesini puanla.

        Args:
            defects: Kusur listesi [{"class_name": str, "length_cm": float}, ...]
            fabric_area_m2: Kumaş alanı (m²)

        Returns:
            QualityReport: Kalite raporu
        """
        defect_scores = []
        total_points = 0
        summary = {}

        for defect in defects:
            class_name = defect.get("class_name", "Unknown")
            length_cm = defect.get("length_cm", 0)

            points, description = self.calculate_defect_points(length_cm)
            total_points += points

            defect_scores.append(DefectScore(
                defect_class=class_name,
                length_cm=length_cm,
                points=points,
                description=description,
            ))

            # Sınıf bazında özet
            if class_name not in summary:
                summary[class_name] = {"count": 0, "points": 0}
            summary[class_name]["count"] += 1
            summary[class_name]["points"] += points

        # 100 m² başına puan hesapla
        if fabric_area_m2 > 0:
            points_per_100m2 = (total_points / fabric_area_m2) * 100
        else:
            points_per_100m2 = 0

        # Kalite sınıfı belirle
        grade = self.calculate_grade(points_per_100m2)

        return QualityReport(
            total_points=total_points,
            points_per_100m2=round(points_per_100m2, 2),
            grade=grade,
            grade_description=self.GRADE_DESCRIPTIONS[grade],
            defect_scores=defect_scores,
            summary=summary,
            fabric_area_m2=fabric_area_m2,
        )

    def get_grade_color(self, grade: QualityGrade) -> str:
        """Kalite sınıfı için renk kodu döndür"""
        colors = {
            QualityGrade.A: "#28a745",  # Yeşil
            QualityGrade.B: "#ffc107",  # Sarı
            QualityGrade.C: "#fd7e14",  # Turuncu
            QualityGrade.REJECT: "#dc3545",  # Kırmızı
        }
        return colors.get(grade, "#6c757d")

    def format_report(self, report: QualityReport) -> str:
        """Raporu okunabilir formatta döndür"""
        lines = [
            "=" * 50,
            "KUMAŞ KALİTE RAPORU",
            "=" * 50,
            f"Kumaş Alanı: {report.fabric_area_m2:.2f} m²",
            f"Toplam Kusur: {len(report.defect_scores)} adet",
            f"Toplam Puan: {report.total_points}",
            f"100 m² Başına Puan: {report.points_per_100m2:.2f}",
            "-" * 50,
            f"KALİTE SINIFI: {report.grade.value}",
            f"Değerlendirme: {report.grade_description}",
            "-" * 50,
            "KUSUR DETAYLARI:",
        ]

        for ds in report.defect_scores:
            lines.append(f"  - {ds.defect_class}: {ds.points} puan ({ds.description})")

        if report.summary:
            lines.append("-" * 50)
            lines.append("ÖZET:")
            for class_name, data in report.summary.items():
                lines.append(f"  - {class_name}: {data['count']} adet, {data['points']} puan")

        lines.append("=" * 50)

        return "\n".join(lines)


if __name__ == "__main__":
    # Test
    scorer = QualityScorer()

    # Örnek kusurlar
    test_defects = [
        {"class_name": "Hole", "length_cm": 5.0},
        {"class_name": "Stain", "length_cm": 12.0},
        {"class_name": "Line", "length_cm": 25.0},
        {"class_name": "Knot", "length_cm": 3.0},
    ]

    report = scorer.score_fabric(test_defects, fabric_area_m2=10.0)
    print(scorer.format_report(report))
