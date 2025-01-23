import onnxruntime as ort
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FaceMatcher:
    def __init__(self, model_path='models/insightface_R100_Glint360K.onnx', threshold=0.5):
        """Initialize face matcher with InsightFace model"""
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.threshold = threshold
        self.known_faces = {}
        
    def preprocess(self, img):
        """Preprocess image for InsightFace model"""
        if img is None or img.size == 0:
            raise ValueError("Invalid image input")
            
        img = cv2.resize(img, (112, 112))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        img = (img - 127.5) / 128.0
        return img.astype(np.float32)
    
    def get_embedding(self, face_img):
        """Get face embedding from image"""
        try:
            preprocessed = self.preprocess(face_img)
            embedding = self.session.run(None, {self.input_name: preprocessed})[0]
            return embedding[0]
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None
    
    def add_face(self, name, face_img):
        """Add a known face to the database"""
        embedding = self.get_embedding(face_img)
        if embedding is not None:
            self.known_faces[name] = embedding
            logger.info(f"Added face for: {name}")
        else:
            logger.error(f"Failed to add face for: {name}")
        
    def find_match(self, face_img):
        """Find matching face in known faces database"""
        embedding = self.get_embedding(face_img)
        if embedding is None:
            return None, 0.0
        
        best_match = None
        best_score = 0
        
        for name, known_emb in self.known_faces.items():
            # Calculate cosine similarity
            similarity = np.dot(embedding, known_emb) / (
                np.linalg.norm(embedding) * np.linalg.norm(known_emb)
            )
            
            if similarity > self.threshold and similarity > best_score:
                best_score = similarity
                best_match = name
                
        return best_match, best_score
