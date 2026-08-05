"""
Instagram Gateway Test Script
اختبر الاتصال بـ Instagram و Firebase قبل الـ deployment
"""

import os
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_instagram_login():
    """اختبر تسجيل الدخول إلى Instagram"""
    print("\n" + "="*60)
    print("🔐 Testing Instagram Login...")
    print("="*60)
    
    try:
        from instagrapi import Client
        from instagrapi.exceptions import BadPassword, LoginRequired
        
        username = os.getenv("INSTAGRAM_USERNAME", "ayemarket2")
        password = os.getenv("INSTAGRAM_PASSWORD")
        
        if not password:
            print("❌ INSTAGRAM_PASSWORD environment variable not set!")
            return False
        
        print(f"📝 Username: {username}")
        print(f"🔑 Password: {'*' * len(password)}")
        
        client = Client()
        print("\n⏳ Logging in...")
        client.login(username, password)
        
        print(f"✅ Successfully logged in as @{username}")
        
        # Get account info
        user_info = client.account_info()
        print(f"   User ID: {user_info.pk}")
        print(f"   Followers: {user_info.follower_count}")
        print(f"   Following: {user_info.following_count}")
        
        return True
    
    except BadPassword:
        print("❌ Invalid Instagram credentials!")
        return False
    except LoginRequired:
        print("❌ Login required - check your credentials")
        return False
    except Exception as e:
        print(f"❌ Instagram login error: {e}")
        return False


def test_firebase_connection():
    """اختبر الاتصال بـ Firebase"""
    print("\n" + "="*60)
    print("🔥 Testing Firebase Connection...")
    print("="*60)
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if not creds_json:
            print("❌ FIREBASE_CREDENTIALS_JSON environment variable not set!")
            return False
        
        print("📋 Firebase Credentials found")
        
        # Parse JSON
        creds_dict = json.loads(creds_json)
        print(f"   Project ID: {creds_dict.get('project_id')}")
        
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.getenv(
                    "FIREBASE_STORAGE_BUCKET",
                    "aye-commercial-4b871.firebasestorage.app"
                )
            })
        
        db = firestore.client()
        
        # Test Firestore connection
        print("\n⏳ Fetching products from Firestore...")
        products = db.collection('products').limit(3).stream()
        
        count = 0
        for doc in products:
            count += 1
            data = doc.to_dict()
            print(f"   • {data.get('title', 'N/A')} (ID: {doc.id})")
        
        print(f"✅ Firebase connected! Found {count} products")
        return True
    
    except json.JSONDecodeError:
        print("❌ Invalid Firebase JSON credentials!")
        return False
    except Exception as e:
        print(f"❌ Firebase error: {e}")
        return False


def test_image_download():
    """اختبر تحميل وتحرير الصور"""
    print("\n" + "="*60)
    print("📸 Testing Image Processing...")
    print("="*60)
    
    try:
        import requests
        from PIL import Image
        from io import BytesIO
        
        # Test image URL
        test_url = "https://via.placeholder.com/1080x1080/3b82f6/ffffff?text=Test+Product"
        
        print(f"📥 Downloading test image from: {test_url}")
        
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        print(f"✅ Image downloaded: {img.size} - {img.mode}")
        
        # Test resize
        max_size = 1080
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        square = Image.new('RGB', (max_size, max_size), (255, 255, 255))
        offset = ((max_size - img.width) // 2, (max_size - img.height) // 2)
        square.paste(img, offset)
        
        print(f"✅ Image processed successfully: {square.size}")
        
        # Save test
        test_path = Path("./test_image.jpg")
        square.save(test_path, "JPEG", quality=95)
        print(f"✅ Test image saved to {test_path}")
        
        # Cleanup
        test_path.unlink()
        
        return True
    
    except Exception as e:
        print(f"❌ Image processing error: {e}")
        return False


def test_firestore_schema():
    """اختبر هيكل مجموعة المنتجات"""
    print("\n" + "="*60)
    print("📋 Testing Firestore Schema...")
    print("="*60)
    
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        db = firestore.client()
        
        # Get a sample product
        products = db.collection('products').limit(1).stream()
        
        sample = None
        for doc in products:
            sample = doc.to_dict()
            sample['id'] = doc.id
            break
        
        if not sample:
            print("⚠️ No products found in Firestore")
            return True
        
        print(f"\n📦 Sample Product Structure:")
        required_fields = ['title', 'description', 'price', 'currency', 'category', 'image']
        
        for field in required_fields:
            value = sample.get(field, "❌ MISSING")
            status = "✅" if field in sample else "❌"
            print(f"   {status} {field}: {str(value)[:50]}")
        
        # Check Instagram fields
        print(f"\n📱 Instagram Fields:")
        print(f"   instagramPosted: {sample.get('instagramPosted', False)}")
        print(f"   instagramMediaId: {sample.get('instagramMediaId', 'N/A')}")
        print(f"   instagramPostTime: {sample.get('instagramPostTime', 'N/A')}")
        
        return True
    
    except Exception as e:
        print(f"❌ Schema test error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  Instagram Gateway - Pre-Deployment Tests".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    results = {
        "Instagram Login": test_instagram_login(),
        "Firebase Connection": test_firebase_connection(),
        "Image Processing": test_image_download(),
        "Firestore Schema": test_firestore_schema(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12} - {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed! Ready for deployment on Render")
    else:
        print("❌ Some tests failed. Check the errors above")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
