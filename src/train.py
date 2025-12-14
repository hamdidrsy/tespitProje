"""
Kumaş Kusur Tespiti - YOLOv8 Segmentation Model Eğitimi
"""

import os
import yaml
from pathlib import Path
from ultralytics import YOLO


def train_model(
    data_yaml: str = "data/data.yaml",
    model_size: str = "n",  # n, s, m, l, x
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    device: str = "0",
    project: str = "runs/segment",
    name: str = "fabric_defect",
    patience: int = 20,
    save_period: int = 10,
):
    """
    YOLOv8 Segmentation modelini eğitir.

    Args:
        data_yaml: Veri seti konfigürasyon dosyası yolu
        model_size: Model boyutu (n=nano, s=small, m=medium, l=large, x=xlarge)
        epochs: Eğitim epoch sayısı
        imgsz: Görüntü boyutu
        batch: Batch boyutu
        device: GPU device (0, 1, 2... veya 'cpu')
        project: Proje klasörü
        name: Eğitim adı
        patience: Early stopping için sabır değeri
        save_period: Kaç epoch'ta bir model kaydedileceği

    Returns:
        Eğitilmiş model ve sonuçlar
    """

    # Model yükle (pretrained)
    model_name = f"yolov8{model_size}-seg.pt"
    print(f"Model yükleniyor: {model_name}")
    model = YOLO(model_name)

    # Eğitim başlat
    print(f"\nEğitim başlatılıyor...")
    print(f"  - Epochs: {epochs}")
    print(f"  - Image Size: {imgsz}")
    print(f"  - Batch Size: {batch}")
    print(f"  - Device: {device}")
    print(f"  - Data: {data_yaml}")

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=project,
        name=name,
        patience=patience,
        save_period=save_period,
        plots=True,
        val=True,
        verbose=True,
    )

    # En iyi modeli kaydet
    best_model_path = Path(project) / name / "weights" / "best.pt"
    target_path = Path("models") / "best.pt"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if best_model_path.exists():
        import shutil
        shutil.copy(best_model_path, target_path)
        print(f"\nEn iyi model kaydedildi: {target_path}")

    return model, results


def validate_model(model_path: str = "models/best.pt", data_yaml: str = "data/data.yaml"):
    """
    Eğitilmiş modeli doğrular.

    Args:
        model_path: Model dosyası yolu
        data_yaml: Veri seti konfigürasyon dosyası yolu

    Returns:
        Doğrulama sonuçları
    """
    model = YOLO(model_path)
    results = model.val(data=data_yaml)

    print("\nDoğrulama Sonuçları:")
    print(f"  - mAP50: {results.seg.map50:.4f}")
    print(f"  - mAP50-95: {results.seg.map:.4f}")

    return results


def export_model(model_path: str = "models/best.pt", format: str = "onnx"):
    """
    Modeli farklı formatlara export eder.

    Args:
        model_path: Model dosyası yolu
        format: Export formatı (onnx, torchscript, openvino, etc.)

    Returns:
        Export edilen dosya yolu
    """
    model = YOLO(model_path)
    export_path = model.export(format=format)
    print(f"Model export edildi: {export_path}")
    return export_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Kumaş Kusur Tespiti Model Eğitimi")
    parser.add_argument("--data", type=str, default="data/data.yaml", help="Data YAML dosyası")
    parser.add_argument("--model", type=str, default="n", help="Model boyutu (n/s/m/l/x)")
    parser.add_argument("--epochs", type=int, default=100, help="Epoch sayısı")
    parser.add_argument("--imgsz", type=int, default=640, help="Görüntü boyutu")
    parser.add_argument("--batch", type=int, default=16, help="Batch boyutu")
    parser.add_argument("--device", type=str, default="0", help="GPU device")
    parser.add_argument("--validate", action="store_true", help="Sadece doğrulama yap")

    args = parser.parse_args()

    if args.validate:
        validate_model()
    else:
        train_model(
            data_yaml=args.data,
            model_size=args.model,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
        )
