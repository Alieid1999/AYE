"""
Unified Gateway - Instagram
بوابة موحدة لنشر المنتجات على انستغرام
"""

import os
import json
import time
import logging
import schedule
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from PIL import Image
from io import BytesIO

import firebase_admin
from firebase_admin import credentials, firestore, storage

from instagrapi import Client as InstaClient
from instagrapi.exceptions import BadPassword, LoginRequired

# ============================================================================
# CONFIGURATION
# ============================================================================

# Firebase
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS_JSON")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "aye-commercial-4b871.firebasestorage.app")

# Instagram
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "ayemarket2")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# State file
STATE_FILE = Path("./gateway_state.json")

# ============================================================================
# UNIFIED GATEWAY CLASS
# ============================================================================

class UnifiedGateway:
    def __init__(self):
        self.db = None
        self.insta_client = None
        self.posted_products = self._load_state()
        
        self._initialize_firebase()
        self._initialize_instagram()
        
        logger.info("✅ Unified Gateway initialized!")
    
    def _load_state(self) -> set:
        """Load previously posted product IDs."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get("posted_ids", []))
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
        return set()
    
    def _save_state(self):
        """Save posted product IDs."""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    "posted_ids": list(self.posted_products),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    # ========================================================================
    # FIREBASE
    # ========================================================================
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if FIREBASE_CREDENTIALS:
                creds_dict = json.loads(FIREBASE_CREDENTIALS)
                cred = credentials.Certificate(creds_dict)
            elif Path("./aye-commercial-4b871-firebase-adminsdk.json").exists():
                cred = credentials.Certificate("./aye-commercial-4b871-firebase-adminsdk.json")
            else:
                logger.error("❌ No Firebase credentials found!")
                return
            
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'storageBucket': FIREBASE_STORAGE_BUCKET
                })
            
            self.db = firestore.client()
            logger.info("✅ Firebase initialized")
        except Exception as e:
            logger.error(f"❌ Firebase error: {e}")
    
    # ========================================================================
    # INSTAGRAM
    # ========================================================================
    
    def _initialize_instagram(self):
        """Initialize Instagram client."""
        try:
            if not INSTAGRAM_PASSWORD:
                logger.warning("⚠️ Instagram password not set, skipping Instagram")
                return
            
            self.insta_client = InstaClient()
            self.insta_client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info(f"✅ Instagram logged in as @{INSTAGRAM_USERNAME}")
        except BadPassword:
            logger.error("❌ Instagram: Invalid credentials")
        except Exception as e:
            logger.error(f"❌ Instagram error: {e}")
    
    def _download_image(self, image_url: str) -> Optional[Image.Image]:
        """Download and process image."""
        try:
            if not image_url:
                return None
            
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Resize
            max_size = 1080
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            square = Image.new('RGB', (max_size, max_size), (255, 255, 255))
            offset = ((max_size - img.width) // 2, (max_size - img.height) // 2)
            square.paste(img, offset)
            
            return square
        except Exception as e:
            logger.error(f"❌ Image download error: {e}")
            return None
    
    def _format_caption(self, product: Dict[str, Any]) -> str:
        """Format product caption."""
        title = product.get('title', 'Product')
        description = product.get('description', '')
        price = product.get('price', 'N/A')
        currency = product.get('currency', 'USD')
        category = product.get('category', 'Tech')
        
        desc_short = description[:180] if description else "Check it out!"
        
        caption = f"""
✨ {title} ✨

📝 {desc_short}

💰 Price: {price} {currency}
🏷️ Category: {category}

🛒 Shop now!
#AYEMarket #TechProducts #{category}
"""
        return caption.strip()
    
    def post_to_instagram(self, product_id: str, product: Dict[str, Any]) -> bool:
        """Post product to Instagram."""
        if not self.insta_client:
            logger.warning("Instagram not initialized")
            return False
        
        try:
            image_url = product.get('image') or product.get('images', [None])[0]
            if not image_url:
                logger.warning(f"Product {product_id} has no image")
                return False
            
            logger.info(f"📸 Posting to Instagram: {product.get('title')}")
            
            img = self._download_image(image_url)
            if not img:
                return False
            
            caption = self._format_caption(product)
            temp_path = f"./temp_{product_id}.jpg"
            img.save(temp_path, "JPEG", quality=95)
            
            result = self.insta_client.photo_upload(temp_path, caption=caption)
            
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            
            logger.info(f"✅ Instagram posted! Media ID: {result.pk}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Instagram error: {e}")
            return False
    
    # ========================================================================
    # MAIN POSTING LOGIC
    # ========================================================================
    
    def post_product_everywhere(self, product_id: str, product: Dict[str, Any]) -> int:
        """Post product to Instagram."""
        success_count = 0
        
        logger.info(f"\n🚀 Posting product: {product.get('title')}")
        logger.info("=" * 60)
        
        # Instagram
        if self.post_to_instagram(product_id, product):
            success_count += 1
            time.sleep(3)
        
        logger.info(f"✅ Posted to {success_count} channel(s)")
        logger.info("=" * 60 + "\n")
        
        return success_count
    
    def check_and_post_new_products(self):
        """Check Firestore for new products and post them."""
        if not self.db:
            logger.error("Firebase not initialized")
            return
        
        try:
            logger.info("🔍 Checking for new products...")
            
            query = self.db.collection('products').where(
                'posted', '==', False
            ).limit(5)
            
            docs = query.stream()
            posted_count = 0
            
            for doc in docs:
                product_id = doc.id
                product_data = doc.to_dict()
                
                if product_id not in self.posted_products:
                    success = self.post_product_everywhere(product_id, product_data)
                    
                    if success > 0:
                        # Mark as posted in Firestore
                        self.db.collection('products').document(product_id).update({
                            'posted': True,
                            'postedTime': datetime.now().isoformat(),
                            'postedChannels': ['instagram'][:success]
                        })
                        
                        self.posted_products.add(product_id)
                        posted_count += 1
                        time.sleep(5)
            
            if posted_count > 0:
                self._save_state()
                logger.info(f"✅ Posted {posted_count} product(s) to Instagram")
            else:
                logger.info("ℹ️ No new products")
        
        except Exception as e:
            logger.error(f"❌ Error: {e}")
    
    def run_scheduler(self):
        """Run the scheduler."""
        schedule.every(10).minutes.do(self.check_and_post_new_products)
        
        logger.info("\n" + "=" * 60)
        logger.info("🚀 UNIFIED GATEWAY STARTED")
        logger.info("=" * 60)
        logger.info("📱 Channels: Instagram")
        logger.info("⏰ Checking every 10 minutes...")
        logger.info("=" * 60 + "\n")
        
        # Run once immediately
        self.check_and_post_new_products()
        
        while True:
            schedule.run_pending()
            time.sleep(60)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    try:
        gateway = UnifiedGateway()
        gateway.run_scheduler()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
