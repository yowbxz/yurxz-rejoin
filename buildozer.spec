[app]
title = YURXZ REJOIN
package.name = yurxzrejoin
package.domain = com.yurxz
source.dir = .
source.include_exts = py,png,jpg,kv,json,html,css,js
source.include_patterns = static/*,static/**/*
version = 1.0
requirements = python3,kivy==2.1.0,requests,pyjnius
orientation = portrait
fullscreen = 1
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 21
android.ndk = 23b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.release_artifact = apk
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 0
