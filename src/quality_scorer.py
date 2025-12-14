"""
Kumaş Kusur Tespiti - Kalite Puanlama Modülü
4-Point Uluslararası Kalite Standardı
Major/Minor Kusur Sınıflandırması

Standart Referans: ASTM D5430 / defect-classifications.pdf
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class DefectSeverity(Enum):
    """Kusur ciddiyeti"""
    MAJOR = "Major"    # Ciddi - ürünü ikinci kalite yapar
    MINOR = "Minor"    # Hafif - konuma göre kabul edilebilir


class QualityGrade(Enum):
    """Kalite sınıfları"""
    A = "A"           # Birinci kalite
    B = "B"           # İkinci kalite
    C = "C"           # Üçüncü kalite
    REJECT = "Ret"    # Kabul edilemez


@dataclass
class DefectScore:
    """Kusur puanı bilgisi"""
    defect_class: str
    severity: DefectSeverity
    length_cm: float
    points: float
    description: str


@dataclass
class QualityReport:
    """Kalite raporu"""
    total_points: float
    major_points: float
    minor_points: float
    points_per_100m2: float
    grade: QualityGrade
    grade_description: str
    defect_scores: List[DefectScore]
    summary: Dict[str, dict]
    fabric_area_m2: float
    fabric_width_cm: float


class QualityScorer:
    """
    4-Point Kalite Puanlama Sistemi

    PDF Standardı (defect-classifications.pdf):

    4-Point Sistemi (kusur uzunluğuna göre):
    - 0-3 inç (0-7.5 cm): 1 puan
    - 3-6 inç (7.5-15 cm): 2 puan
    - 6-9 inç (15-23 cm): 3 puan
    - 9+ inç (23+ cm): 4 puan

    Major/Minor Sistemi (kusur ciddiyetine göre):
    - Major: Her 9 inç (23 cm) için 1 puan
    - Minor: Her 9 inç (23 cm) için 0.25 puan (1/4 puan)

    Kurallar:
    - Bir lineer metre/yard'da maksimum 4 puan
    - Kabul sınırı: 40 puan / 100 m²
    """

    # 9 inç = 22.86 cm ≈ 23 cm (PDF standardı)
    INCH_9_CM = 23.0

    # 4-Point System kuralları (kusur uzunluğuna göre puan)
    FOUR_POINT_RULES = [
        (7.5, 1),    # 0-3 inç (0-7.5 cm): 1 puan
        (15.0, 2),   # 3-6 inç (7.5-15 cm): 2 puan
        (23.0, 3),   # 6-9 inç (15-23 cm): 3 puan
        (float('inf'), 4),  # 9+ inç (23+ cm): 4 puan
    ]

    # Kusur türlerinin Major/Minor sınıflandırması
    DEFECT_SEVERITY = {
        "Hole": DefectSeverity.MAJOR,    # Delik - her zaman major
        "Stain": DefectSeverity.MAJOR,   # Leke - genellikle major
        "Line": DefectSeverity.MINOR,    # Çizgi - genellikle minor
        "Knot": DefectSeverity.MINOR,    # Düğüm - genellikle minor
    }

    # Kalite sınıfı eşikleri (100 m² başına puan)
    # PDF'e göre 40 puan/100m² kabul edilebilir sınır
    GRADE_THRESHOLDS = {
        QualityGrade.A: (0, 20),           # 0-20 puan: A sınıfı (Birinci)
        QualityGrade.B: (20, 40),          # 20-40 puan: B sınıfı (İkinci)
        QualityGrade.C: (40, 60),          # 40-60 puan: C sınıfı (Üçüncü)
        QualityGrade.REJECT: (60, float('inf')),  # >60 puan: Ret
    }

    GRADE_DESCRIPTIONS = {
        QualityGrade.A: "Birinci Kalite - Mükemmel",
        QualityGrade.B: "İkinci Kalite - Kabul Edilebilir",
        QualityGrade.C: "Üçüncü Kalite - Sınırlı Kullanım",
        QualityGrade.REJECT: "Ret - Kabul Edilemez",
    }

    SEVERITY_TR = {
        DefectSeverity.MAJOR: "Majör",
        DefectSeverity.MINOR: "Minör",
    }

    def __init__(
        self,
        max_points_per_100m2: float = 40.0,
        use_major_minor_system: bool = True,
    ):
        """
        Args:
            max_points_per_100m2: 100 m² başına maksimum kabul edilebilir puan
            use_major_minor_system: Major/Minor sistemi kullan (False ise sadece 4-Point)
        """
        self.max_points_per_100m2 = max_points_per_100m2
        self.use_major_minor_system = use_major_minor_system

    def get_defect_severity(self, class_name: str, length_cm: float) -> DefectSeverity:
        """
        Kusur ciddiyetini belirle.

        Args:
            class_name: Kusur sınıfı
            length_cm: Kusur uzunluğu

        Returns:
            DefectSeverity: Kusur ciddiyeti
        """
        base_severity = self.DEFECT_SEVERITY.get(class_name, DefectSeverity.MINOR)

        # 9 inç (23 cm)'den uzun kusurlar her zaman major
        if length_cm > self.INCH_9_CM:
            return DefectSeverity.MAJOR

        return base_severity

    def calculate_four_point_score(self, length_cm: float) -> Tuple[int, str]:
        """
        4-Point sistemine göre puan hesapla.

        PDF Standardı:
        - 0-3 inç (0-7.5 cm): 1 puan
        - 3-6 inç (7.5-15 cm): 2 puan
        - 6-9 inç (15-23 cm): 3 puan
        - 9+ inç (23+ cm): 4 puan

        Args:
            length_cm: Kusur uzunluğu (cm)

        Returns:
            (puan, açıklama) tuple
        """
        for threshold, points in self.FOUR_POINT_RULES:
            if length_cm <= threshold:
                if points == 1:
                    desc = f"0-3 inç / 0-7.5 cm ({length_cm:.1f} cm)"
                elif points == 2:
                    desc = f"3-6 inç / 7.5-15 cm ({length_cm:.1f} cm)"
                elif points == 3:
                    desc = f"6-9 inç / 15-23 cm ({length_cm:.1f} cm)"
                else:
                    desc = f"9+ inç / 23+ cm ({length_cm:.1f} cm)"
                return points, desc

        return 4, f"9+ inç / 23+ cm ({length_cm:.1f} cm)"

    def calculate_major_minor_score(
        self,
        length_cm: float,
        severity: DefectSeverity,
    ) -> Tuple[float, str]:
        """
        Major/Minor sistemine göre puan hesapla.

        PDF Standardı:
        - Major: Her 9 inç (23 cm) için 1 puan
        - Minor: Her 9 inç (23 cm) için 0.25 puan (1/4 puan)

        Args:
            length_cm: Kusur uzunluğu
            severity: Kusur ciddiyeti

        Returns:
            (puan, açıklama) tuple
        """
        # 9 inç (23 cm) increment sayısı (yukarı yuvarla)
        increments = max(1, -(-int(length_cm) // int(self.INCH_9_CM)))  # ceiling division

        if severity == DefectSeverity.MAJOR:
            points = increments * 1.0
            desc = f"Majör: {increments}x1.0 puan ({length_cm:.1f} cm)"
        else:
            points = increments * 0.25
            desc = f"Minör: {increments}x0.25 puan ({length_cm:.1f} cm)"

        # Maksimum 4 puan kuralı (bir lineer metrede)
        points = min(points, 4.0)

        return points, desc

    def calculate_defect_points(
        self,
        class_name: str,
        length_cm: float,
    ) -> Tuple[float, DefectSeverity, str]:
        """
        Kusur puanını hesapla.

        Args:
            class_name: Kusur sınıfı
            length_cm: Kusur uzunluğu

        Returns:
            (puan, ciddiyet, açıklama) tuple
        """
        severity = self.get_defect_severity(class_name, length_cm)

        if self.use_major_minor_system:
            points, desc = self.calculate_major_minor_score(length_cm, severity)
        else:
            points, desc = self.calculate_four_point_score(length_cm)
            # 4-Point sisteminde severity sadece bilgi amaçlı

        return points, severity, desc

    def calculate_grade(self, points_per_100m2: float) -> QualityGrade:
        """
        Puana göre kalite sınıfı belirle.

        Args:
            points_per_100m2: 100 m² başına puan

        Returns:
            QualityGrade: Kalite sınıfı
        """
        for grade, (min_pts, max_pts) in self.GRADE_THRESHOLDS.items():
            if min_pts <= points_per_100m2 < max_pts:
                return grade

        return QualityGrade.REJECT

    def score_fabric(
        self,
        defects: List[dict],
        fabric_area_m2: float = 1.0,
        fabric_width_cm: float = 150.0,
    ) -> QualityReport:
        """
        Kumaş kalitesini puanla.

        Args:
            defects: Kusur listesi [{"class_name": str, "length_cm": float}, ...]
            fabric_area_m2: Kumaş alanı (m²)
            fabric_width_cm: Kumaş genişliği (cm)

        Returns:
            QualityReport: Kalite raporu
        """
        defect_scores = []
        total_points = 0.0
        major_points = 0.0
        minor_points = 0.0
        summary = {}

        for defect in defects:
            class_name = defect.get("class_name", "Unknown")
            length_cm = defect.get("length_cm", 0)

            points, severity, description = self.calculate_defect_points(class_name, length_cm)
            total_points += points

            if severity == DefectSeverity.MAJOR:
                major_points += points
            else:
                minor_points += points

            defect_scores.append(DefectScore(
                defect_class=class_name,
                severity=severity,
                length_cm=length_cm,
                points=points,
                description=description,
            ))

            # Sınıf bazında özet
            if class_name not in summary:
                summary[class_name] = {
                    "count": 0,
                    "points": 0,
                    "major_count": 0,
                    "minor_count": 0,
                }
            summary[class_name]["count"] += 1
            summary[class_name]["points"] += points
            if severity == DefectSeverity.MAJOR:
                summary[class_name]["major_count"] += 1
            else:
                summary[class_name]["minor_count"] += 1

        # 100 m² başına puan hesapla
        if fabric_area_m2 > 0:
            points_per_100m2 = (total_points / fabric_area_m2) * 100
        else:
            points_per_100m2 = 0

        # Kalite sınıfı belirle
        grade = self.calculate_grade(points_per_100m2)

        return QualityReport(
            total_points=round(total_points, 2),
            major_points=round(major_points, 2),
            minor_points=round(minor_points, 2),
            points_per_100m2=round(points_per_100m2, 2),
            grade=grade,
            grade_description=self.GRADE_DESCRIPTIONS[grade],
            defect_scores=defect_scores,
            summary=summary,
            fabric_area_m2=fabric_area_m2,
            fabric_width_cm=fabric_width_cm,
        )

    def get_grade_color(self, grade: QualityGrade) -> str:
        """Kalite sınıfı için renk kodu döndür"""
        colors = {
            QualityGrade.A: "#28a745",     # Yeşil
            QualityGrade.B: "#ffc107",     # Sarı
            QualityGrade.C: "#fd7e14",     # Turuncu
            QualityGrade.REJECT: "#dc3545", # Kırmızı
        }
        return colors.get(grade, "#6c757d")

    def format_report(self, report: QualityReport) -> str:
        """Raporu okunabilir formatta döndür"""
        lines = [
            "=" * 50,
            "KUMAŞ KALİTE RAPORU",
            "4-Point / Major-Minor Standardı",
            "=" * 50,
            f"Kumaş Alanı: {report.fabric_area_m2:.2f} m²",
            f"Kumaş Genişliği: {report.fabric_width_cm:.0f} cm",
            f"Toplam Kusur: {len(report.defect_scores)} adet",
            "-" * 50,
            "PUANLAMA:",
            f"  Majör Puanlar: {report.major_points:.2f}",
            f"  Minör Puanlar: {report.minor_points:.2f}",
            f"  Toplam Puan: {report.total_points:.2f}",
            f"  100 m² Başına: {report.points_per_100m2:.2f} puan",
            "-" * 50,
            f"KALİTE SINIFI: {report.grade.value}",
            f"Değerlendirme: {report.grade_description}",
            "-" * 50,
            "KUSUR DETAYLARI:",
        ]

        for ds in report.defect_scores:
            severity_tr = self.SEVERITY_TR.get(ds.severity, ds.severity.value)
            lines.append(f"  - {ds.defect_class} [{severity_tr}]: {ds.points:.2f} puan ({ds.description})")

        if report.summary:
            lines.append("-" * 50)
            lines.append("ÖZET:")
            for class_name, data in report.summary.items():
                lines.append(
                    f"  - {class_name}: {data['count']} adet "
                    f"({data['major_count']} majör, {data['minor_count']} minör), "
                    f"{data['points']:.2f} puan"
                )

        lines.append("=" * 50)
        lines.append("Standart: 4-Point System (ASTM D5430)")
        lines.append("Major: 1 puan / 9 inç (23 cm)")
        lines.append("Minor: 0.25 puan / 9 inç (23 cm)")
        lines.append(f"Kabul Sınırı: {self.max_points_per_100m2} puan/100m²")
        lines.append("=" * 50)

        return "\n".join(lines)


if __name__ == "__main__":
    # Test
    scorer = QualityScorer()

    # Örnek kusurlar
    test_defects = [
        {"class_name": "Hole", "length_cm": 5.0},      # Major - 1 puan
        {"class_name": "Stain", "length_cm": 12.0},    # Major - 1 puan
        {"class_name": "Line", "length_cm": 30.0},     # Minor->Major (uzun) - 2 puan
        {"class_name": "Knot", "length_cm": 3.0},      # Minor - 0.25 puan
    ]

    report = scorer.score_fabric(test_defects, fabric_area_m2=10.0)
    print(scorer.format_report(report))
