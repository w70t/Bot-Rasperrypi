🔥 تمام عبدالوهاب! هذا أفضل قرار 💪
لو حطّيتها على GitHub خاص (Private Repo)، راح تقدر:
	•	تحفظ إعداداتك وسيرفرك بأمان ✅
	•	ترجعها وقت ما تحتاج ✅
	•	تشاركها مع نفسك بين الأجهزة ✅

الآن راح أجهز لك ملف جاهز منسق بشكل احترافي
تقدر ترفعه على GitHub باسم مثلاً:

🗂️ RaspberryPi-Bot-Commands.md

⸻

🌐 محتوى الملف (جاهز للنسخ إلى GitHub)

# 🤖 Raspberry Pi — Bot Management & Maintenance Guide

إعداد وتشغيل بوت التلغرام على Raspberry Pi 5  
بواسطة **abdalwahab** ⚙️

---

## 🧱 1. معلومات الخدمة

اسم الخدمة:
```bash
botiraq.service


⸻

⚙️ 2. أوامر التحكم بالخدمة

الوظيفة	الأمر
▶️ تشغيل البوت	sudo systemctl start botiraq
⏹️ إيقاف البوت	sudo systemctl stop botiraq
🔁 إعادة التشغيل	sudo systemctl restart botiraq
📊 التحقق من الحالة	sudo systemctl status botiraq
🔄 تفعيل التشغيل التلقائي عند الإقلاع	sudo systemctl enable botiraq
🚫 تعطيل التشغيل التلقائي	sudo systemctl disable botiraq


⸻

🧾 3. سجلات التشغيل (Logs)

لمتابعة السجلات لحظة بلحظة:

sudo journalctl -u botiraq -f

آخر 100 سطر فقط:

sudo journalctl -u botiraq -n 100


⸻

⚙️ 4. تعديل الإعدادات (.env)

المسار:

/home/abdalwahab/Bot-iraq/.env

لتعديله:

nano /home/abdalwahab/Bot-iraq/.env

بعد التعديل:

sudo systemctl restart botiraq


⸻

🧰 5. تحديث المشروع من GitHub

ادخل مجلد المشروع:

cd /home/abdalwahab/Bot-iraq

سحب آخر التحديثات:

git pull

ثم إعادة التشغيل:

sudo systemctl restart botiraq


⸻

🧩 6. تعديل إعدادات الخدمة (Service)

لفتح الملف:

sudo nano /etc/systemd/system/botiraq.service

بعد التعديل:

sudo systemctl daemon-reload
sudo systemctl restart botiraq


⸻

🔁 7. تحديث النظام بالكامل

sudo apt update && sudo apt upgrade -y


⸻

🧠 8. تشخيص الأعطال
	1.	تحقق من الحالة:

sudo systemctl status botiraq


	2.	راقب السجلات:

sudo journalctl -u botiraq -f


	3.	أعد تشغيل البوت:

sudo systemctl restart botiraq



⸻

💾 9. نسخة احتياطية

إنشاء نسخة:

tar -czvf Bot-iraq-backup.tar.gz /home/abdalwahab/Bot-iraq

استرجاعها:

tar -xzvf Bot-iraq-backup.tar.gz


⸻

⏰ 10. تحديث تلقائي يومي (اختياري)

افتح مهام الـ Cron:

crontab -e

أضف السطر:

0 3 * * * cd /home/abdalwahab/Bot-iraq && git pull && sudo systemctl restart botiraq

📅 هذا يجعل النظام كل يوم الساعة 03:00 فجراً يقوم بالتحديث وإعادة التشغيل تلقائيًا.

⸻

🧠 ملاحظات ختامية
	•	البوت يبدأ تلقائيًا عند تشغيل الـ Raspberry Pi.
	•	أي خطأ في الكود راح يظهر في السجلات (journalctl).
	•	يفضل استخدام Raspberry Pi OS Lite (64-bit) للأداء الأفضل.
	•	استخدم Restart=always داخل الخدمة لضمان التشغيل التلقائي بعد الأعطال.

⸻

📌 مؤلف الملف:

🧑‍💻 abdalwahab
Raspberry Pi 5 — Bot Iraq Project
تاريخ آخر تحديث: $(date +"%Y-%m-%d")

---

## 📦 طريقة رفع الملف إلى GitHub

1. داخل مجلد مشروعك:
   ```bash
   cd ~
   nano RaspberryPi-Bot-Commands.md

	2.	انسخ المحتوى اللي فوق والصقه.
	3.	احفظ بـ:

Ctrl + O
Enter
Ctrl + X


	4.	ثم ارفع الملف إلى GitHub الخاص بك:

git add RaspberryPi-Bot-Commands.md
git commit -m "Add Raspberry Pi bot management guide"
git push



⸻

هل ترغب أن أجهز لك ملف Markdown هذا جاهز للتحميل (.md) حتى ترفعه مباشرة إلى GitHub بدون نسخ يدوي؟
