"""
Kumaş Kusur Tespiti - Detector Modülü
YOLOv8 Segmentation ile kusur tespiti ve analizi
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from ultralytics import YOLO


@dataclass
class Defect:
    """Tespit edilen kusur bilgisi"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    mask: Optional[np.ndarray] = None
    area_pixels: float = 0.0
    area_cm2: float = 0.0
    length_cm: float = 0.0
    width_cm: float = 0.0

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": self.bbox,
            "area_pixels": round(self.area_pixels, 2),
            "area_cm2": round(self.area_cm2, 2),
            "length_cm": round(self.length_cm, 2),
            "width_cm": round(self.width_cm, 2),
        }


@dataclass
class DetectionResult:
    """Tespit sonuçları"""
    image: np.ndarray
    defects: List[Defect] = field(default_factory=list)
    annotated_image: Optional[np.ndarray] = None
    total_defects: int = 0
    defect_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_defects": self.total_defects,
            "defect_summary": self.defect_summary,
            "defects": [d.to_dict() for d in self.defects],
        }


class FabricDefectDetector:
    """Kumaş kusur tespit sınıfı"""

    CLASS_NAMES = {0: "Hole", 1: "Knot", 2: "Line", 3: "Stain"}
    CLASS_NAMES_TR = {"Hole": "Delik", "Knot": "Düğüm", "Line": "Çizgi", "Stain": "Leke"}
    CLASS_COLORS = {
        "Hole": (0, 0, 255),      # Kırmızı
        "Knot": (0, 165, 255),    # Turuncu
        "Line": (0, 255, 255),    # Sarı
        "Stain": (255, 0, 255),   # Mor
    }

    def __init__(
        self,
        model_path: str = "models/best.pt",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = "0",
    ):
        """
        Detector'ı başlat.

        Args:
            model_path: YOLOv8 model dosyası yolu
            conf_threshold: Güven eşiği
            iou_threshold: IoU eşiği
            device: GPU device
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model = None

        self._load_model()

    def _load_model(self):
        """Modeli yükle"""
        if Path(self.model_path).exists():
            self.model = YOLO(self.model_path)
            print(f"Model yüklendi: {self.model_path}")
        else:
            print(f"Model bulunamadı: {self.model_path}")
            print("Lütfen önce modeli eğitin: python src/train.py")

    def detect(
        self,
        image: Union[str, np.ndarray],
        dpi: float = 96,
        fabric_width_cm: float = 150,
        conf_threshold: Optional[float] = None,
    ) -> DetectionResult:
        """
        Görüntüde kusur tespiti yap.

        Args:
            image: Görüntü dosya yolu veya numpy array
            dpi: Görüntü DPI değeri (piksel/inç)
            fabric_width_cm: Kumaş genişliği (cm)
            conf_threshold: Güven eşiği (None ise varsayılan kullanılır)

        Returns:
            DetectionResult: Tespit sonuçları
        """
        # Güven eşiğini belirle
        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        # Görüntüyü yükle
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f"Görüntü yüklenemedi: {image}")
        else:
            img = image.copy()

        # Piksel -> cm dönüşüm faktörü
        pixels_per_cm = self._calculate_pixels_per_cm(img.shape[1], fabric_width_cm)

        result = DetectionResult(image=img)

        if self.model is None:
            print("Model yüklenmemiş!")
            return result

        # YOLOv8 inference
        predictions = self.model.predict(
            source=img,
            conf=conf,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )

        # Sonuçları işle
        defects = []
        defect_counts = {name: 0 for name in self.CLASS_NAMES.values()}

        for pred in predictions:
            if pred.masks is None:
                continue

            boxes = pred.boxes
            masks = pred.masks

            for i in range(len(boxes)):
                # Sınıf ve güven
                class_id = int(boxes.cls[i])
                confidence = float(boxes.conf[i])
                class_name = self.CLASS_NAMES.get(class_id, f"Unknown_{class_id}")

                # Bounding box
                x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())

                # Mask
                mask = masks.data[i].cpu().numpy()
                mask = cv2.resize(mask, (img.shape[1], img.shape[0]))
                mask = (mask > 0.5).astype(np.uint8)

                # Boyut hesaplamaları
                area_pixels = np.sum(mask)
                area_cm2 = area_pixels / (pixels_per_cm ** 2)

                # Uzunluk ve genişlik (bounding box'tan)
                length_pixels = max(x2 - x1, y2 - y1)
                width_pixels = min(x2 - x1, y2 - y1)
                length_cm = length_pixels / pixels_per_cm
                width_cm = width_pixels / pixels_per_cm

                defect = Defect(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    mask=mask,
                    area_pixels=area_pixels,
                    area_cm2=area_cm2,
                    length_cm=length_cm,
                    width_cm=width_cm,
                )
                defects.append(defect)
                defect_counts[class_name] += 1

        result.defects = defects
        result.total_defects = len(defects)
        result.defect_summary = defect_counts
        result.annotated_image = self._annotate_image(img, defects)

        return result

    def _calculate_pixels_per_cm(self, image_width: int, fabric_width_cm: float) -> float:
        """Piksel/cm oranını hesapla"""
        return image_width / fabric_width_cm

    def _annotate_image(self, image: np.ndarray, defects: List[Defect]) -> np.ndarray:
        """Görüntüye kusurları çiz"""
        annotated = image.copy()

        for defect in defects:
            color = self.CLASS_COLORS.get(defect.class_name, (255, 255, 255))
            x1, y1, x2, y2 = defect.bbox

            # Mask overlay
            if defect.mask is not None:
                mask_colored = np.zeros_like(annotated)
                mask_colored[defect.mask > 0] = color
                annotated = cv2.addWeighted(annotated, 1, mask_colored, 0.3, 0)

            # Bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label
            label = f"{defect.class_name}: {defect.confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(
                annotated,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )

        return annotated

    def get_class_name_tr(self, class_name: str) -> str:
        """İngilizce sınıf adını Türkçe'ye çevir"""
        return self.CLASS_NAMES_TR.get(class_name, class_name)


if __name__ == "__main__":
    # Test
    detector = FabricDefectDetector()

    # Test görüntüsü
    test_image = "data/test/images/1_jpg.rf.56d2f34ef7702a2b5a659ca26feedc0c.jpg"
    if Path(test_image).exists():
        result = detector.detect(test_image)
        print(f"Toplam kusur: {result.total_defects}")
        print(f"Kusur özeti: {result.defect_summary}")
        for defect in result.defects:
            print(f"  - {defect.class_name}: {defect.length_cm:.2f} cm")
