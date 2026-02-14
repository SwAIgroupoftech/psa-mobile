[app]

title = PSA Mobile
package.name = psamobile
package.domain = org.psa
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json
version = 1.0.0

requirements = python3==3.11.0,hostpython3==3.11.0,kivy==2.3.0,pillow,requests,certifi,urllib3,idna,charset-normalizer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.private_storage = True
android.skip_update = False
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
