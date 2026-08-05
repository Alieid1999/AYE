"""
Instagram Gateway - Auto-posts products from Firestore to Instagram
Runs on Render.com
"""

import os
import time
import logging
import schedule
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from PIL import Image
from io import BytesIO

import firebase_admin
from firebase_admin import credentials, firestore, storage

from instagrapi import Client
from instagrapi.exceptions import BadPassword, LoginRequired

# ============================================================================
# CONFIGURATION
# ============================================================================

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "ayemarket2")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "Qwertyuiop1@")

# Firebase credentials from environment or local file
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS_JSON")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "aye-commercial-4b871.firebasestorage.app")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# State file to track already-posted products
STATE_FILE = Path("./instagram_state.json")

# ============================================================================
# INSTAGRAM CLIENT
# ============================================================================

class InstagramGateway:
    def __init__(self):
        self.client = None
        self.db = None
        self.posted_products = self._load_state()
        self._initialize_firebase()
        self._initialize_instagram()
    
    def _load_state(self) -> set:
        """Load previously posted product IDs from state file."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get("posted_ids", []))
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return set()
    
    def _save_state(self):
        """Save posted product IDs to state file."""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    "posted_ids": list(self.posted_products),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if FIREBASE_CREDENTIALS:
                # Load from JSON string (environment variable)
                creds_dict = json.loads(FIREBASE_CREDENTIALS)
                cred = credentials.Certificate(creds_dict)
            elif Path("./aye-commercial-4b871-firebase-adminsdk.json").exists():
                # Load from local file
                cred = credentials.Certificate("./aye-commercial-4b871-firebase-adminsdk.json")
            else:
                logger.error("No Firebase credentials found!")
                return
            
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'storageBucket': FIREBASE_STORAGE_BUCKET
                })
            
            self.db = firestore.client()
            logger.info("✅ Firebase initialized successfully")
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            raise
    
    def _initialize_instagram(self):
        """Initialize Instagram client with login."""
        try:
            self.client = Client()
            self.client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info(f"✅ Logged into Instagram as @{INSTAGRAM_USERNAME}")
        except BadPassword:
            logger.error("❌ Instagram login failed: Invalid credentials")
            raise
        except LoginRequired:
            logger.error("❌ Instagram login required: Invalid session")
            raise
        except Exception as e:
            logger.error(f"❌ Instagram initialization failed: {e}")
            raise
    
    def _download_image(self, image_url: str) -> Optional[Image.Image]:
        """Download image from URL and return PIL Image object."""
        try:
            if not image_url:
                logger.warning("Image URL is empty")
                return None
            
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            
            # Convert RGBA to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Resize to Instagram optimal size (1080x1080 for square)
            max_size = 1080
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Center image in a square canvas
            square = Image.new('RGB', (max_size, max_size), (255, 255, 255))
            offset = ((max_size - img.width) // 2, (max_size - img.height) // 2)
            square.paste(img, offset)
            
            logger.info(f"📸 Image downloaded and processed: {img.size}")
            return square
        except Exception as e:
            logger.error(f"❌ Failed to download image: {e}")
            return None
    
    def _format_caption(self, product: Dict[str, Any]) -> str:
        """Format product data into Instagram caption."""
        title = product.get('title', 'Product')
        description = product.get('description', '')
        price = product.get('price', 'N/A')
        currency = product.get('currency', 'USD')
        category = product.get('category', 'Tech')
        
        # Limit description to 2000 chars (Instagram limit ~2200)
        desc_short = description[:180] if description else "Check out this amazing product!"
        
        caption = f"""
✨ {title} ✨

📝 {desc_short}

💰 Price: {price} {currency}
🏷️ Category: {category}

🛒 Shop now via our store!
.
.
#AYEMarket #TechProducts #OnlineShopping #{category} #NewProduct #{title.replace(' ', '')}
"""
        return caption.strip()
    
    def post_product(self, product_id: str, product: Dict[str, Any]) -> bool:
        """Post a product to Instagram."""
        try:
            image_url = product.get('image') or product.get('images', [None])[0]
            if not image_url:
                logger.warning(f"⚠️ Product {product_id} has no image, skipping")
                return False
            
            logger.info(f"📤 Posting product: {product.get('title', 'Unknown')}")
            
            # Download and prepare image
            img = self._download_image(image_url)
            if not img:
                logger.error(f"Failed to process image for product {product_id}")
                return False
            
            # Format caption
            caption = self._format_caption(product)
            
            # Save temp image file
            temp_path = f"./temp_{product_id}.jpg"
            img.save(temp_path, "JPEG", quality=95)
            
            # Post to Instagram
            result = self.client.photo_upload(temp_path, caption=caption)
            
            # Cleanup
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            
            # Save to Firestore that it was posted
            self.db.collection('products').document(product_id).update({
                'instagramPosted': True,
                'instagramMediaId': result.pk,
                'instagramPostTime': datetime.now().isoformat()
            })
            
            logger.info(f"✅ Successfully posted to Instagram! Media ID: {result.pk}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to post product {product_id}: {e}")
            return False
    
    def check_new_products(self):
        """Check Firestore for new products and post them."""
        if not self.db:
            logger.error("Firebase not initialized")
            return
        
        try:
            logger.info("🔍 Checking for new products...")
            
            # Query products that haven't been posted to Instagram
            query = self.db.collection('products').where(
                'instagramPosted', '==', False
            ).limit(5)  # Process max 5 at a time
            
            docs = query.stream()
            posted_count = 0
            
            for doc in docs:
                product_id = doc.id
                product_data = doc.to_dict()
                
                if product_id not in self.posted_products:
                    logger.info(f"📌 Found new product: {product_data.get('title')}")
                    
                    if self.post_product(product_id, product_data):
                        self.posted_products.add(product_id)
                        posted_count += 1
                        
                        # Wait between posts to avoid rate limiting
                        time.sleep(5)
            
            if posted_count > 0:
                self._save_state()
                logger.info(f"✅ Posted {posted_count} product(s) to Instagram")
            else:
                logger.info("ℹ️ No new products to post")
        
        except Exception as e:
            logger.error(f"❌ Error checking products: {e}")
    
    def run_scheduler(self):
        """Run the scheduler that checks for new products periodically."""
        # Check every 10 minutes
        schedule.every(10).minutes.do(self.check_new_products)
        
        logger.info("🚀 Instagram Gateway scheduler started")
        logger.info("⏰ Checking for new products every 10 minutes...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    try:
        logger.info("=" * 60)
        logger.info("🎬 Instagram Gateway Starting...")
        logger.info("=" * 60)
        
        gateway = InstagramGateway()
        
        # Run one check immediately
        gateway.check_new_products()
        
        # Start the scheduler
        gateway.run_scheduler()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Shutting down Instagram Gateway...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
