import logging
import os

class ModelLoader:
    """
    Central utility to download and cache PyTorch/ONNX models needed by the microservices.
    Ensures that heavy weight architectures are loaded only once and reside in memory.
    """
    
    def __init__(self, cache_dir="./models"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        logging.getLogger(__name__).info(f"ModelLoader initialized with cache dir: {self.cache_dir}")

    def load_yolo_face_model(self):
        # Stub: Download/Load YOLOv11 for face tracking
        logging.info("Loading YOLOv11 Face model...")
        return "YOLOv11_Model_Instance"

    def load_expression_model(self):
        # Stub: Download/Load AffectNet transformer model
        logging.info("Loading AffectNet Expression model...")
        return "AffectNet_Model_Instance"
        
    def load_rppg_extractor(self):
        # Stub: POS / CHROM algorithm initialization, potentially a deep network backbone
        logging.info("Loading rPPG extraction pipelines...")
        return "rPPG_Pipeline"

model_loader = ModelLoader()
