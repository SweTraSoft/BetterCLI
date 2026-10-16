"""Small built-in UI translations with system-language detection."""

from __future__ import annotations

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QApplication

LANGUAGE_SYSTEM = "system"
LANGUAGES = (
    ("en", "English"),
    ("es", "Español"),
    ("zh", "简体中文"),
    ("hi", "हिन्दी"),
    ("ar", "العربية"),
    ("pt", "Português"),
    ("bn", "বাংলা"),
    ("ru", "Русский"),
    ("ja", "日本語"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("tr", "Türkçe"),
    ("id", "Bahasa Indonesia"),
    ("ko", "한국어"),
    ("ur", "اردو"),
    ("sv", "Svenska"),
)

_TEXT = {
    "Settings": {
        "es": "Configuración", "zh": "设置", "hi": "सेटिंग्स", "ar": "الإعدادات",
        "pt": "Configurações", "bn": "সেটিংস", "ru": "Настройки", "ja": "設定",
        "de": "Einstellungen", "fr": "Paramètres", "tr": "Ayarlar", "id": "Pengaturan",
        "ko": "설정", "ur": "ترتیبات",
    },
    "Appearance": {
        "es": "Apariencia", "zh": "外观", "hi": "रूप", "ar": "المظهر", "pt": "Aparência",
        "bn": "চেহারা", "ru": "Оформление", "ja": "外観", "de": "Erscheinungsbild",
        "fr": "Apparence", "tr": "Görünüm", "id": "Tampilan", "ko": "모양", "ur": "ظاہری شکل",
    },
    "Language": {
        "es": "Idioma", "zh": "语言", "hi": "भाषा", "ar": "اللغة", "pt": "Idioma",
        "bn": "ভাষা", "ru": "Язык", "ja": "言語", "de": "Sprache", "fr": "Langue",
        "tr": "Dil", "id": "Bahasa", "ko": "언어", "ur": "زبان",
    },
    "Version": {
        "es": "Versión", "zh": "版本", "hi": "संस्करण", "ar": "الإصدار", "pt": "Versão",
        "bn": "সংস্করণ", "ru": "Версия", "ja": "バージョン", "de": "Version",
        "fr": "Version", "tr": "Sürüm", "id": "Versi", "ko": "버전", "ur": "ورژن",
    },
    "Light": {
        "es": "Claro", "zh": "浅色", "hi": "हल्का", "ar": "فاتح", "pt": "Claro",
        "bn": "হালকা", "ru": "Светлая", "ja": "ライト", "de": "Hell", "fr": "Clair",
        "tr": "Açık", "id": "Terang", "ko": "라이트", "ur": "روشن",
    },
    "Dark": {
        "es": "Oscuro", "zh": "深色", "hi": "गहरा", "ar": "داكن", "pt": "Escuro",
        "bn": "গাঢ়", "ru": "Тёмная", "ja": "ダーク", "de": "Dunkel", "fr": "Sombre",
        "tr": "Koyu", "id": "Gelap", "ko": "다크", "ur": "گہرا",
    },
    "Follow system": {
        "es": "Seguir el sistema", "zh": "跟随系统", "hi": "सिस्टम का अनुसरण करें",
        "ar": "اتباع النظام", "pt": "Seguir o sistema", "bn": "সিস্টেম অনুসরণ করুন",
        "ru": "Как в системе", "ja": "システムに従う", "de": "System folgen",
        "fr": "Suivre le système", "tr": "Sistemi izle", "id": "Ikuti sistem",
        "ko": "시스템 설정 따르기", "ur": "سسٹم کے مطابق",
    },
    "System language": {
        "es": "Idioma del sistema", "zh": "系统语言", "hi": "सिस्टम भाषा", "ar": "لغة النظام",
        "pt": "Idioma do sistema", "bn": "সিস্টেমের ভাষা", "ru": "Язык системы",
        "ja": "システムの言語", "de": "Systemsprache", "fr": "Langue du système",
        "tr": "Sistem dili", "id": "Bahasa sistem", "ko": "시스템 언어", "ur": "سسٹم کی زبان",
    },
    "Recent commands": {
        "es": "Comandos recientes", "zh": "最近使用的命令", "hi": "हाल के कमांड",
        "ar": "الأوامر الأخيرة", "pt": "Comandos recentes", "bn": "সাম্প্রতিক কমান্ড",
        "ru": "Недавние команды", "ja": "最近のコマンド", "de": "Letzte Befehle",
        "fr": "Commandes récentes", "tr": "Son komutlar", "id": "Perintah terbaru",
        "ko": "최근 명령", "ur": "حالیہ کمانڈز",
    },
    "No recent commands": {
        "es": "No hay comandos recientes", "zh": "没有最近使用的命令", "hi": "कोई हालिया कमांड नहीं",
        "ar": "لا توجد أوامر أخيرة", "pt": "Não há comandos recentes", "bn": "কোনো সাম্প্রতিক কমান্ড নেই",
        "ru": "Нет недавних команд", "ja": "最近のコマンドはありません", "de": "Keine letzten Befehle",
        "fr": "Aucune commande récente", "tr": "Son komut yok", "id": "Tidak ada perintah terbaru",
        "ko": "최근 명령이 없습니다", "ur": "کوئی حالیہ کمانڈ نہیں",
    },
    "New Session": {
        "es": "Nueva sesión", "zh": "新会话", "hi": "नया सत्र", "ar": "جلسة جديدة",
        "pt": "Nova sessão", "bn": "নতুন সেশন", "ru": "Новый сеанс", "ja": "新しいセッション",
        "de": "Neue Sitzung", "fr": "Nouvelle session", "tr": "Yeni oturum",
        "id": "Sesi baru", "ko": "새 세션", "ur": "نیا سیشن",
    },
    "Start a new command": {
        "es": "Iniciar un nuevo comando", "zh": "开始新命令", "hi": "नया कमांड शुरू करें",
        "ar": "ابدأ أمرًا جديدًا", "pt": "Iniciar um novo comando", "bn": "নতুন কমান্ড শুরু করুন",
        "ru": "Начать новую команду", "ja": "新しいコマンドを開始", "de": "Einen neuen Befehl starten",
        "fr": "Démarrer une nouvelle commande", "tr": "Yeni bir komut başlat",
        "id": "Mulai perintah baru", "ko": "새 명령 시작", "ur": "نئی کمانڈ شروع کریں",
    },
    "Discover": {
        "es": "Detectar", "zh": "读取", "hi": "खोजें", "ar": "استكشاف", "pt": "Descobrir",
        "bn": "খুঁজুন", "ru": "Найти", "ja": "検出", "de": "Erkennen", "fr": "Découvrir",
        "tr": "Keşfet", "id": "Temukan", "ko": "검색", "ur": "دریافت کریں",
    },
    "Show help text": {
        "es": "Mostrar texto de ayuda", "zh": "显示帮助文本", "hi": "सहायता पाठ दिखाएँ",
        "ar": "إظهار نص المساعدة", "pt": "Mostrar texto de ajuda", "bn": "সহায়তা পাঠ দেখান",
        "ru": "Показать справку", "ja": "ヘルプを表示", "de": "Hilfetext anzeigen",
        "fr": "Afficher l’aide", "tr": "Yardım metnini göster", "id": "Tampilkan teks bantuan",
        "ko": "도움말 표시", "ur": "مدد کا متن دکھائیں",
    },
    "Working directory (defaults to your home)": {
        "es": "Directorio de trabajo (por defecto, tu carpeta personal)",
        "zh": "工作目录（默认为主目录）", "hi": "कार्य निर्देशिका (डिफ़ॉल्ट: आपका होम फ़ोल्डर)",
        "ar": "مجلد العمل (الافتراضي هو المجلد الرئيسي)", "pt": "Diretório de trabalho (padrão: sua pasta pessoal)",
        "bn": "কাজের ডিরেক্টরি (ডিফল্ট আপনার হোম ফোল্ডার)", "ru": "Рабочая папка (по умолчанию домашняя)",
        "ja": "作業ディレクトリ（既定はホーム）", "de": "Arbeitsverzeichnis (Standard: Benutzerordner)",
        "fr": "Répertoire de travail (par défaut : dossier personnel)", "tr": "Çalışma dizini (varsayılan: ana dizininiz)",
        "id": "Direktori kerja (bawaan: folder home)", "ko": "작업 디렉터리 (기본값: 홈 폴더)",
        "ur": "کام کی ڈائریکٹری (طے شدہ: ہوم فولڈر)",
    },
    "Choose…": {
        "es": "Elegir…", "zh": "选择…", "hi": "चुनें…", "ar": "اختر…", "pt": "Escolher…",
        "bn": "নির্বাচন…", "ru": "Выбрать…", "ja": "選択…", "de": "Auswählen…",
        "fr": "Choisir…", "tr": "Seç…", "id": "Pilih…", "ko": "선택…", "ur": "منتخب کریں…",
    },
    "Copy": {
        "es": "Copiar", "zh": "复制", "hi": "कॉपी", "ar": "نسخ", "pt": "Copiar",
        "bn": "কপি", "ru": "Копировать", "ja": "コピー", "de": "Kopieren",
        "fr": "Copier", "tr": "Kopyala", "id": "Salin", "ko": "복사", "ur": "کاپی",
    },
    "Run": {
        "es": "Ejecutar", "zh": "运行", "hi": "चलाएँ", "ar": "تشغيل", "pt": "Executar",
        "bn": "চালান", "ru": "Запустить", "ja": "実行", "de": "Ausführen", "fr": "Exécuter",
        "tr": "Çalıştır", "id": "Jalankan", "ko": "실행", "ur": "چلائیں",
    },
    "Cancel": {
        "es": "Cancelar", "zh": "取消", "hi": "रद्द करें", "ar": "إلغاء", "pt": "Cancelar",
        "bn": "বাতিল", "ru": "Отмена", "ja": "キャンセル", "de": "Abbrechen", "fr": "Annuler",
        "tr": "İptal", "id": "Batal", "ko": "취소", "ur": "منسوخ",
    },
    "Command Line Interface": {
        "es": "Interfaz de línea de comandos", "zh": "命令行界面", "hi": "कमांड लाइन इंटरफ़ेस",
        "ar": "واجهة سطر الأوامر", "pt": "Interface de linha de comando", "bn": "কমান্ড লাইন ইন্টারফেস",
        "ru": "Интерфейс командной строки", "ja": "コマンドライン インターフェース",
        "de": "Kommandozeile", "fr": "Interface en ligne de commande",
        "tr": "Komut satırı arayüzü", "id": "Antarmuka baris perintah",
        "ko": "명령줄 인터페이스", "ur": "کمانڈ لائن انٹرفیس",
    },
    "Output": {
        "es": "Salida", "zh": "输出", "hi": "आउटपुट", "ar": "الإخراج", "pt": "Saída",
        "bn": "আউটপুট", "ru": "Вывод", "ja": "出力", "de": "Ausgabe", "fr": "Sortie",
        "tr": "Çıktı", "id": "Keluaran", "ko": "출력", "ur": "آؤٹ پٹ",
    },
    "Explore CLI commands": {
        "es": "Explorar comandos CLI", "zh": "浏览命令行命令", "hi": "CLI कमांड खोजें",
        "ar": "استكشاف أوامر CLI", "pt": "Explorar comandos CLI", "bn": "CLI কমান্ড দেখুন",
        "ru": "Обзор команд CLI", "ja": "CLI コマンドを探す", "de": "CLI-Befehle erkunden",
        "fr": "Explorer les commandes CLI", "tr": "CLI komutlarını keşfet",
        "id": "Jelajahi perintah CLI", "ko": "CLI 명령 탐색", "ur": "CLI کمانڈز دیکھیں",
    },
    "Clear": {
        "es": "Limpiar", "zh": "清除", "hi": "साफ़ करें", "ar": "مسح", "pt": "Limpar",
        "bn": "মুছুন", "ru": "Очистить", "ja": "クリア", "de": "Leeren", "fr": "Effacer",
        "tr": "Temizle", "id": "Bersihkan", "ko": "지우기", "ur": "صاف کریں",
    },
    "Tools": {
        "es": "Herramientas", "zh": "工具", "hi": "उपकरण", "ar": "الأدوات", "pt": "Ferramentas",
        "bn": "সরঞ্জাম", "ru": "Инструменты", "ja": "ツール", "de": "Werkzeuge", "fr": "Outils",
        "tr": "Araçlar", "id": "Alat", "ko": "도구", "ur": "اوزار",
    },
    "Arguments": {
        "es": "Argumentos", "zh": "参数", "hi": "आर्ग्युमेंट", "ar": "وسائط", "pt": "Argumentos",
        "bn": "আর্গুমেন্ট", "ru": "Аргументы", "ja": "引数", "de": "Argumente", "fr": "Arguments",
        "tr": "Bağımsız değişkenler", "id": "Argumen", "ko": "인수", "ur": "آرگومنٹس",
    },
    "Required options": {
        "es": "Opciones obligatorias", "zh": "必需选项", "hi": "आवश्यक विकल्प",
        "ar": "الخيارات المطلوبة", "pt": "Opções obrigatórias", "bn": "প্রয়োজনীয় বিকল্প",
        "ru": "Обязательные параметры", "ja": "必須オプション", "de": "Erforderliche Optionen",
        "fr": "Options requises", "tr": "Gerekli seçenekler", "id": "Opsi wajib",
        "ko": "필수 옵션", "ur": "ضروری اختیارات",
    },
    "Options": {
        "es": "Opciones", "zh": "选项", "hi": "विकल्प", "ar": "الخيارات", "pt": "Opções",
        "bn": "বিকল্প", "ru": "Параметры", "ja": "オプション", "de": "Optionen", "fr": "Options",
        "tr": "Seçenekler", "id": "Opsi", "ko": "옵션", "ur": "اختیارات",
    },
    "Additional arguments": {
        "es": "Argumentos adicionales", "zh": "其他参数", "hi": "अतिरिक्त आर्ग्युमेंट",
        "ar": "وسائط إضافية", "pt": "Argumentos adicionais", "bn": "অতিরিক্ত আর্গুমেন্ট",
        "ru": "Дополнительные аргументы", "ja": "追加の引数", "de": "Zusätzliche Argumente",
        "fr": "Arguments supplémentaires", "tr": "Ek bağımsız değişkenler",
        "id": "Argumen tambahan", "ko": "추가 인수", "ur": "اضافی آرگومنٹس",
    },
    "optional": {
        "es": "opcional", "zh": "可选", "hi": "वैकल्पिक", "ar": "اختياري", "pt": "opcional",
        "bn": "ঐচ্ছিক", "ru": "необязательно", "ja": "任意", "de": "optional",
        "fr": "facultatif", "tr": "isteğe bağlı", "id": "opsional", "ko": "선택 사항", "ur": "اختیاری",
    },
    "Command output appears here.": {
        "es": "La salida del comando aparecerá aquí.", "zh": "命令输出将显示在此处。",
        "hi": "कमांड का आउटपुट यहाँ दिखाई देगा।", "ar": "سيظهر ناتج الأمر هنا.",
        "pt": "A saída do comando aparecerá aqui.", "bn": "কমান্ডের আউটপুট এখানে দেখা যাবে।",
        "ru": "Здесь появится вывод команды.", "ja": "コマンドの出力がここに表示されます。",
        "de": "Die Befehlsausgabe erscheint hier.", "fr": "La sortie de la commande apparaîtra ici.",
        "tr": "Komut çıktısı burada görünür.", "id": "Keluaran perintah akan muncul di sini.",
        "ko": "명령 출력이 여기에 표시됩니다.", "ur": "کمانڈ کا آؤٹ پٹ یہاں دکھائی دے گا۔",
    },
    "Enter a command above and press Discover.": {
        "es": "Introduce un comando arriba y pulsa Detectar.",
        "zh": "在上方输入命令并点击“读取”。", "hi": "ऊपर कमांड दर्ज करें और खोजें दबाएँ।",
        "ar": "أدخل أمرًا أعلاه واضغط على استكشاف.", "pt": "Digite um comando acima e clique em Descobrir.",
        "bn": "উপরে একটি কমান্ড লিখে খুঁজুন চাপুন।", "ru": "Введите команду выше и нажмите «Найти».",
        "ja": "上にコマンドを入力して「検出」を押してください。",
        "de": "Geben Sie oben einen Befehl ein und klicken Sie auf „Erkennen“.",
        "fr": "Saisissez une commande ci-dessus et cliquez sur Découvrir.",
        "tr": "Yukarıya bir komut girip Keşfet'e basın.", "id": "Masukkan perintah di atas lalu tekan Temukan.",
        "ko": "위에 명령을 입력하고 검색을 누르세요.", "ur": "اوپر کمانڈ درج کریں اور دریافت کریں دبائیں۔",
    },
    "You can still pass arguments using the field above.": {
        "es": "Aún puedes pasar argumentos usando el campo de arriba.",
        "zh": "你仍可使用上方字段传入参数。", "hi": "आप ऊपर दिए गए फ़ील्ड से आर्ग्युमेंट दे सकते हैं।",
        "ar": "لا يزال بإمكانك تمرير الوسائط باستخدام الحقل أعلاه.",
        "pt": "Ainda é possível passar argumentos usando o campo acima.",
        "bn": "উপরের ক্ষেত্রটি ব্যবহার করে এখনও আর্গুমেন্ট দিতে পারেন।",
        "ru": "Вы по-прежнему можете передать аргументы в поле выше.",
        "ja": "上のフィールドから引数を渡すこともできます。",
        "de": "Sie können Argumente weiterhin über das Feld oben übergeben.",
        "fr": "Vous pouvez toujours transmettre des arguments dans le champ ci-dessus.",
        "tr": "Yukarıdaki alanı kullanarak bağımsız değişkenleri iletebilirsiniz.",
        "id": "Anda tetap dapat memasukkan argumen melalui kolom di atas.",
        "ko": "위 필드에서 인수를 전달할 수 있습니다.",
        "ur": "آپ اوپر والے خانے سے آرگومنٹس دے سکتے ہیں۔",
    },
    "Ready": {
        "es": "Listo", "zh": "就绪", "hi": "तैयार", "ar": "جاهز", "pt": "Pronto",
        "bn": "প্রস্তুত", "ru": "Готово", "ja": "準備完了", "de": "Bereit",
        "fr": "Prêt", "tr": "Hazır", "id": "Siap", "ko": "준비됨", "ur": "تیار",
    },
    "Command history cleared": {
        "es": "Historial de comandos borrado", "zh": "命令历史已清除", "hi": "कमांड इतिहास साफ़ किया गया",
        "ar": "تم مسح سجل الأوامر", "pt": "Histórico de comandos limpo", "bn": "কমান্ড ইতিহাস মুছে ফেলা হয়েছে",
        "ru": "История команд очищена", "ja": "コマンド履歴を消去しました", "de": "Befehlsverlauf gelöscht",
        "fr": "Historique des commandes effacé", "tr": "Komut geçmişi temizlendi",
        "id": "Riwayat perintah dihapus", "ko": "명령 기록을 지웠습니다", "ur": "کمانڈ کی ہسٹری صاف کر دی گئی",
    },
    "Command copied to the clipboard": {
        "es": "Comando copiado al portapapeles", "zh": "命令已复制到剪贴板", "hi": "कमांड क्लिपबोर्ड पर कॉपी किया गया",
        "ar": "تم نسخ الأمر إلى الحافظة", "pt": "Comando copiado para a área de transferência",
        "bn": "কমান্ড ক্লিপবোর্ডে কপি করা হয়েছে", "ru": "Команда скопирована в буфер обмена",
        "ja": "コマンドをクリップボードにコピーしました", "de": "Befehl in die Zwischenablage kopiert",
        "fr": "Commande copiée dans le presse-papiers", "tr": "Komut panoya kopyalandı",
        "id": "Perintah disalin ke papan klip", "ko": "명령을 클립보드에 복사했습니다",
        "ur": "کمانڈ کلپ بورڈ پر کاپی ہو گئی",
    },
    "Settings saved": {
        "es": "Configuración guardada", "zh": "设置已保存", "hi": "सेटिंग्स सहेजी गईं",
        "ar": "تم حفظ الإعدادات", "pt": "Configurações salvas", "bn": "সেটিংস সংরক্ষিত হয়েছে",
        "ru": "Настройки сохранены", "ja": "設定を保存しました", "de": "Einstellungen gespeichert",
        "fr": "Paramètres enregistrés", "tr": "Ayarlar kaydedildi", "id": "Pengaturan disimpan",
        "ko": "설정을 저장했습니다", "ur": "ترتیبات محفوظ ہو گئیں",
    },
    "Settings…": {
        "es": "Configuración…", "zh": "设置…", "hi": "सेटिंग्स…", "ar": "الإعدادات…",
        "pt": "Configurações…", "bn": "সেটিংস…", "ru": "Настройки…", "ja": "設定…",
        "de": "Einstellungen…", "fr": "Paramètres…", "tr": "Ayarlar…",
        "id": "Pengaturan…", "ko": "설정…", "ur": "ترتیبات…",
    },
    "Save": {
        "es": "Guardar", "zh": "保存", "hi": "सहेजें", "ar": "حفظ", "pt": "Salvar",
        "bn": "সংরক্ষণ", "ru": "Сохранить", "ja": "保存", "de": "Speichern",
        "fr": "Enregistrer", "tr": "Kaydet", "id": "Simpan", "ko": "저장", "ur": "محفوظ کریں",
    },
    "Clear command history": {
        "es": "Borrar historial de comandos", "zh": "清除命令历史", "hi": "कमांड इतिहास साफ़ करें",
        "ar": "مسح سجل الأوامر", "pt": "Limpar histórico de comandos", "bn": "কমান্ড ইতিহাস মুছুন",
        "ru": "Очистить историю команд", "ja": "コマンド履歴を消去", "de": "Befehlsverlauf löschen",
        "fr": "Effacer l’historique des commandes", "tr": "Komut geçmişini temizle",
        "id": "Hapus riwayat perintah", "ko": "명령 기록 지우기", "ur": "کمانڈ ہسٹری صاف کریں",
    },
    "Clear the output below": {
        "es": "Borrar la salida de abajo", "zh": "清除下方输出", "hi": "नीचे का आउटपुट साफ़ करें",
        "ar": "امسح المخرجات أدناه", "pt": "Limpar a saída abaixo", "bn": "নিচের আউটপুট মুছুন",
        "ru": "Очистить вывод ниже", "ja": "下の出力を消去", "de": "Die Ausgabe unten leeren",
        "fr": "Effacer la sortie ci-dessous", "tr": "Aşağıdaki çıktıyı temizle",
        "id": "Bersihkan keluaran di bawah", "ko": "아래 출력 지우기", "ur": "نیچے کا آؤٹ پٹ صاف کریں",
    },
    "Command to configure, e.g. rsync, git log, ffmpeg": {
        "es": "Comando que configurar, p. ej., rsync, git log, ffmpeg",
        "zh": "要配置的命令，例如 rsync、git log、ffmpeg", "hi": "कॉन्फ़िगर करने का कमांड, जैसे rsync, git log, ffmpeg",
        "ar": "الأمر المطلوب إعداده، مثل rsync أو git log أو ffmpeg",
        "pt": "Comando a configurar, por exemplo rsync, git log, ffmpeg",
        "bn": "কনফিগার করার কমান্ড, যেমন rsync, git log, ffmpeg",
        "ru": "Команда для настройки, например rsync, git log, ffmpeg",
        "ja": "設定するコマンド（例: rsync、git log、ffmpeg）",
        "de": "Zu konfigurierender Befehl, z. B. rsync, git log, ffmpeg",
        "fr": "Commande à configurer, p. ex. rsync, git log, ffmpeg",
        "tr": "Yapılandırılacak komut; ör. rsync, git log, ffmpeg",
        "id": "Perintah yang dikonfigurasi, mis. rsync, git log, ffmpeg",
        "ko": "구성할 명령(예: rsync, git log, ffmpeg)",
        "ur": "ترتیب دینے کی کمانڈ، مثلاً rsync، git log، ffmpeg",
    },
    "Open a subcommand of the current command": {
        "es": "Abrir un subcomando del comando actual", "zh": "打开当前命令的子命令",
        "hi": "मौजूदा कमांड का सब-कमांड खोलें", "ar": "افتح أمرًا فرعيًا للأمر الحالي",
        "pt": "Abrir um subcomando do comando atual", "bn": "বর্তমান কমান্ডের সাবকমান্ড খুলুন",
        "ru": "Открыть подкоманду текущей команды", "ja": "現在のコマンドのサブコマンドを開く",
        "de": "Unterbefehl des aktuellen Befehls öffnen", "fr": "Ouvrir une sous-commande",
        "tr": "Geçerli komutun alt komutunu aç", "id": "Buka subperintah dari perintah saat ini",
        "ko": "현재 명령의 하위 명령 열기", "ur": "موجودہ کمانڈ کی ذیلی کمانڈ کھولیں",
    },
    "Clear discovery cache": {
        "es": "Borrar caché de detección", "zh": "清除发现缓存", "hi": "खोज कैश साफ़ करें",
        "ar": "مسح ذاكرة التخزين المؤقت للاستكشاف", "pt": "Limpar cache de descoberta",
        "bn": "আবিষ্কার ক্যাশে মুছুন", "ru": "Очистить кэш поиска", "ja": "検出キャッシュを消去",
        "de": "Erkennungscache leeren", "fr": "Vider le cache de découverte",
        "tr": "Keşif önbelleğini temizle", "id": "Hapus cache penemuan",
        "ko": "검색 캐시 지우기", "ur": "دریافت کیش صاف کریں",
    },
    "No options were discovered for this command. You can still pass arguments using the field above.": {
        "es": "No se detectaron opciones. Aún puedes pasar argumentos con el campo de arriba.",
        "zh": "未发现此命令的选项。你仍可使用上方字段传入参数。",
        "hi": "इस कमांड के लिए कोई विकल्प नहीं मिला। आप ऊपर के फ़ील्ड से आर्ग्युमेंट दे सकते हैं।",
        "ar": "لم يتم اكتشاف خيارات لهذا الأمر. يمكنك تمرير الوسائط باستخدام الحقل أعلاه.",
        "pt": "Nenhuma opção foi descoberta. Ainda é possível passar argumentos no campo acima.",
        "bn": "এই কমান্ডের কোনো বিকল্প পাওয়া যায়নি। উপরের ক্ষেত্র দিয়ে আর্গুমেন্ট দিতে পারেন।",
        "ru": "Для команды не найдены параметры. Аргументы можно передать в поле выше.",
        "ja": "このコマンドのオプションは見つかりませんでした。上の欄から引数を渡せます。",
        "de": "Für diesen Befehl wurden keine Optionen gefunden. Argumente können Sie oben eingeben.",
        "fr": "Aucune option trouvée. Vous pouvez toujours saisir des arguments dans le champ ci-dessus.",
        "tr": "Bu komut için seçenek bulunamadı. Yukarıdaki alandan bağımsız değişken verebilirsiniz.",
        "id": "Tidak ada opsi untuk perintah ini. Anda tetap dapat memasukkan argumen di kolom atas.",
        "ko": "이 명령의 옵션을 찾지 못했습니다. 위 필드에서 인수를 전달할 수 있습니다.",
        "ur": "اس کمانڈ کے لیے کوئی اختیارات نہیں ملے۔ آپ اوپر والے خانے سے آرگومنٹس دے سکتے ہیں۔",
    },
    "Anything not listed above, e.g. --flag value": {
        "es": "Cualquier otro argumento, p. ej. --flag value",
        "zh": "其他未列出的参数，例如 --flag value", "hi": "ऊपर सूचीबद्ध नहीं, जैसे --flag value",
        "ar": "أي شيء غير مدرج أعلاه، مثل --flag value", "pt": "Qualquer argumento não listado, por exemplo --flag value",
        "bn": "উপরে তালিকাভুক্ত নয় এমন কিছু, যেমন --flag value", "ru": "Другие аргументы, например --flag value",
        "ja": "上記以外の引数（例: --flag value）", "de": "Nicht aufgeführte Argumente, z. B. --flag value",
        "fr": "Tout argument non répertorié, p. ex. --flag value", "tr": "Listelenmeyenler, ör. --flag value",
        "id": "Argumen lain yang tidak tercantum, mis. --flag value", "ko": "목록에 없는 인수(예: --flag value)",
        "ur": "اوپر درج نہ ہو، مثلاً --flag value",
    },
    "extra": {
        "es": "extra", "zh": "其他", "hi": "अतिरिक्त", "ar": "إضافي", "pt": "extra",
        "bn": "অতিরিক্ত", "ru": "дополнительно", "ja": "追加", "de": "zusätzlich",
        "fr": "supplément", "tr": "ekstra", "id": "tambahan", "ko": "추가", "ur": "اضافی",
    },
    "comma-separated values": {
        "es": "valores separados por comas", "zh": "逗号分隔的值", "hi": "अल्पविराम से अलग मान",
        "ar": "قيم مفصولة بفواصل", "pt": "valores separados por vírgula", "bn": "কমা দিয়ে পৃথক করা মান",
        "ru": "значения через запятую", "ja": "カンマ区切りの値", "de": "kommagetrennte Werte",
        "fr": "valeurs séparées par des virgules", "tr": "virgülle ayrılmış değerler",
        "id": "nilai dipisahkan koma", "ko": "쉼표로 구분된 값", "ur": "کوما سے جدا قدریں",
    },
    "Choose files or folders": {
        "es": "Elegir archivos o carpetas", "zh": "选择文件或文件夹", "hi": "फ़ाइलें या फ़ोल्डर चुनें",
        "ar": "اختر ملفات أو مجلدات", "pt": "Escolher arquivos ou pastas", "bn": "ফাইল বা ফোল্ডার নির্বাচন করুন",
        "ru": "Выбрать файлы или папки", "ja": "ファイルまたはフォルダーを選択",
        "de": "Dateien oder Ordner auswählen", "fr": "Choisir des fichiers ou dossiers",
        "tr": "Dosya veya klasör seç", "id": "Pilih file atau folder", "ko": "파일 또는 폴더 선택",
        "ur": "فائلیں یا فولڈرز منتخب کریں",
    },
    "Choose": {
        "es": "Elegir", "zh": "选择", "hi": "चुनें", "ar": "اختر", "pt": "Escolher",
        "bn": "নির্বাচন", "ru": "Выбрать", "ja": "選択", "de": "Auswählen", "fr": "Choisir",
        "tr": "Seç", "id": "Pilih", "ko": "선택", "ur": "منتخب کریں",
    },
    "Browse…": {
        "es": "Examinar…", "zh": "浏览…", "hi": "ब्राउज़…", "ar": "استعراض…",
        "pt": "Procurar…", "bn": "ব্রাউজ…", "ru": "Обзор…", "ja": "参照…",
        "de": "Durchsuchen…", "fr": "Parcourir…", "tr": "Gözat…", "id": "Jelajahi…",
        "ko": "찾아보기…", "ur": "براؤز کریں…",
    },
    "directory path": {
        "es": "ruta de directorio", "zh": "目录路径", "hi": "निर्देशिका पथ", "ar": "مسار المجلد",
        "pt": "caminho do diretório", "bn": "ডিরেক্টরির পথ", "ru": "путь к папке",
        "ja": "ディレクトリパス", "de": "Verzeichnispfad", "fr": "chemin du dossier",
        "tr": "dizin yolu", "id": "jalur direktori", "ko": "디렉터리 경로", "ur": "ڈائریکٹری کا راستہ",
    },
    "file or directory path": {
        "es": "ruta de archivo o directorio", "zh": "文件或目录路径", "hi": "फ़ाइल या निर्देशिका पथ",
        "ar": "مسار ملف أو مجلد", "pt": "caminho de arquivo ou diretório", "bn": "ফাইল বা ডিরেক্টরির পথ",
        "ru": "путь к файлу или папке", "ja": "ファイルまたはディレクトリのパス",
        "de": "Datei- oder Verzeichnispfad", "fr": "chemin de fichier ou dossier",
        "tr": "dosya veya dizin yolu", "id": "jalur file atau direktori", "ko": "파일 또는 디렉터리 경로",
        "ur": "فائل یا ڈائریکٹری کا راستہ",
    },
    "Choose a directory": {
        "es": "Elegir un directorio", "zh": "选择目录", "hi": "निर्देशिका चुनें", "ar": "اختر مجلدًا",
        "pt": "Escolher um diretório", "bn": "একটি ডিরেক্টরি নির্বাচন করুন", "ru": "Выбрать папку",
        "ja": "ディレクトリを選択", "de": "Verzeichnis auswählen", "fr": "Choisir un dossier",
        "tr": "Bir dizin seç", "id": "Pilih direktori", "ko": "디렉터리 선택", "ur": "ڈائریکٹری منتخب کریں",
    },
    "Working directory": {
        "es": "Directorio de trabajo", "zh": "工作目录", "hi": "कार्य निर्देशिका", "ar": "مجلد العمل",
        "pt": "Diretório de trabalho", "bn": "কাজের ডিরেক্টরি", "ru": "Рабочая папка",
        "ja": "作業ディレクトリ", "de": "Arbeitsverzeichnis", "fr": "Répertoire de travail",
        "tr": "Çalışma dizini", "id": "Direktori kerja", "ko": "작업 디렉터리", "ur": "کام کی ڈائریکٹری",
    },
    "You can type here directly.": {
        "es": "Puedes escribir aquí directamente.", "zh": "你可以直接在此处输入。",
        "hi": "आप यहाँ सीधे टाइप कर सकते हैं।", "ar": "يمكنك الكتابة هنا مباشرة.",
        "pt": "Você pode digitar aqui diretamente.", "bn": "আপনি এখানে সরাসরি টাইপ করতে পারেন।",
        "ru": "Здесь можно вводить команду напрямую.", "ja": "ここに直接入力できます。",
        "de": "Sie können hier direkt eingeben.", "fr": "Vous pouvez saisir directement ici.",
        "tr": "Buraya doğrudan yazabilirsiniz.", "id": "Anda dapat mengetik langsung di sini.",
        "ko": "여기에 직접 입력할 수 있습니다.", "ur": "آپ یہاں براہ راست لکھ سکتے ہیں۔",
    },
    "Invalid command: check for unmatched quotes": {
        "es": "Comando no válido: comprueba las comillas sin cerrar",
        "zh": "命令无效：检查是否有未配对的引号", "hi": "अमान्य कमांड: बिना जोड़े उद्धरण चिह्न जाँचें",
        "ar": "أمر غير صالح: تحقق من علامات الاقتباس غير المتطابقة",
        "pt": "Comando inválido: verifique aspas sem par", "bn": "অবৈধ কমান্ড: জোড়াহীন উদ্ধৃতি চিহ্ন পরীক্ষা করুন",
        "ru": "Некорректная команда: проверьте кавычки", "ja": "無効なコマンド: 対応しない引用符を確認してください",
        "de": "Ungültiger Befehl: Prüfen Sie nicht geschlossene Anführungszeichen",
        "fr": "Commande invalide : vérifiez les guillemets non fermés",
        "tr": "Geçersiz komut: eşleşmeyen tırnakları kontrol edin",
        "id": "Perintah tidak valid: periksa tanda kutip yang tidak berpasangan",
        "ko": "잘못된 명령: 짝이 맞지 않는 따옴표를 확인하세요",
        "ur": "غلط کمانڈ: نامکمل اقتباسی نشانات دیکھیں",
    },
    "Reading --help…": {
        "es": "Leyendo --help…", "zh": "正在读取 --help…", "hi": "--help पढ़ रहा है…",
        "ar": "جارٍ قراءة --help…", "pt": "Lendo --help…", "bn": "--help পড়া হচ্ছে…",
        "ru": "Чтение --help…", "ja": "--help を読み込み中…", "de": "--help wird gelesen…",
        "fr": "Lecture de --help…", "tr": "--help okunuyor…", "id": "Membaca --help…",
        "ko": "--help 읽는 중…", "ur": "--help پڑھا جا رہا ہے…",
    },
    "Discovery failed": {
        "es": "Error al detectar", "zh": "读取失败", "hi": "खोज विफल", "ar": "فشل الاستكشاف",
        "pt": "Falha ao descobrir", "bn": "খুঁজে পাওয়া যায়নি", "ru": "Не удалось найти",
        "ja": "検出に失敗しました", "de": "Erkennung fehlgeschlagen", "fr": "Échec de la découverte",
        "tr": "Keşif başarısız", "id": "Penemuan gagal", "ko": "검색 실패", "ur": "دریافت ناکام",
    },
    "Cannot read that command": {
        "es": "No se puede leer ese comando", "zh": "无法读取该命令", "hi": "उस कमांड को पढ़ नहीं सकते",
        "ar": "تعذرت قراءة هذا الأمر", "pt": "Não é possível ler esse comando",
        "bn": "কমান্ডটি পড়া যাচ্ছে না", "ru": "Не удалось прочитать эту команду",
        "ja": "このコマンドを読み取れません", "de": "Dieser Befehl kann nicht gelesen werden",
        "fr": "Impossible de lire cette commande", "tr": "Bu komut okunamıyor",
        "id": "Tidak dapat membaca perintah tersebut", "ko": "해당 명령을 읽을 수 없습니다",
        "ur": "یہ کمانڈ پڑھی نہیں جا سکتی",
    },
    "Could not discover options": {
        "es": "No se pudieron detectar las opciones", "zh": "无法发现选项", "hi": "विकल्प नहीं खोज सके",
        "ar": "تعذر استكشاف الخيارات", "pt": "Não foi possível descobrir as opções",
        "bn": "বিকল্প খুঁজে পাওয়া যায়নি", "ru": "Не удалось найти параметры",
        "ja": "オプションを検出できませんでした", "de": "Optionen konnten nicht erkannt werden",
        "fr": "Impossible de découvrir les options", "tr": "Seçenekler bulunamadı",
        "id": "Tidak dapat menemukan opsi", "ko": "옵션을 찾을 수 없습니다", "ur": "اختیارات دریافت نہیں ہو سکے",
    },
    "Could not start": {
        "es": "No se pudo iniciar", "zh": "无法启动", "hi": "शुरू नहीं कर सके", "ar": "تعذر البدء",
        "pt": "Não foi possível iniciar", "bn": "শুরু করা যায়নি", "ru": "Не удалось запустить",
        "ja": "起動できませんでした", "de": "Starten nicht möglich", "fr": "Impossible de démarrer",
        "tr": "Başlatılamadı", "id": "Tidak dapat memulai", "ko": "시작할 수 없습니다",
        "ur": "شروع نہیں ہو سکا",
    },
    "Run anyway": {
        "es": "Ejecutar de todos modos", "zh": "仍然运行", "hi": "फिर भी चलाएँ", "ar": "تشغيل على أي حال",
        "pt": "Executar mesmo assim", "bn": "তারপরও চালান", "ru": "Всё равно запустить",
        "ja": "それでも実行", "de": "Trotzdem ausführen", "fr": "Exécuter quand même",
        "tr": "Yine de çalıştır", "id": "Tetap jalankan", "ko": "무시하고 실행", "ur": "پھر بھی چلائیں",
    },
    "Type RUN to enable the button": {
        "es": "Escribe RUN para habilitar el botón", "zh": "输入 RUN 以启用按钮",
        "hi": "बटन सक्षम करने के लिए RUN लिखें", "ar": "اكتب RUN لتفعيل الزر",
        "pt": "Digite RUN para habilitar o botão", "bn": "বোতাম সক্রিয় করতে RUN লিখুন",
        "ru": "Введите RUN, чтобы активировать кнопку", "ja": "ボタンを有効にするには RUN と入力",
        "de": "Geben Sie RUN ein, um die Schaltfläche zu aktivieren",
        "fr": "Saisissez RUN pour activer le bouton", "tr": "Düğmeyi etkinleştirmek için RUN yazın",
        "id": "Ketik RUN untuk mengaktifkan tombol", "ko": "버튼을 활성화하려면 RUN 입력",
        "ur": "بٹن فعال کرنے کے لیے RUN لکھیں",
    },
    "Review before running": {
        "es": "Revisar antes de ejecutar", "zh": "运行前检查", "hi": "चलाने से पहले समीक्षा करें",
        "ar": "راجع قبل التشغيل", "pt": "Revisar antes de executar", "bn": "চালানোর আগে পর্যালোচনা করুন",
        "ru": "Проверка перед запуском", "ja": "実行前に確認", "de": "Vor dem Ausführen prüfen",
        "fr": "Vérifier avant l’exécution", "tr": "Çalıştırmadan önce gözden geçir",
        "id": "Tinjau sebelum menjalankan", "ko": "실행 전 검토", "ur": "چلانے سے پہلے جائزہ لیں",
    },
    "This command looks dangerous.": {
        "es": "Este comando parece peligroso.", "zh": "此命令似乎有危险。", "hi": "यह कमांड खतरनाक लगती है।",
        "ar": "يبدو هذا الأمر خطيرًا.", "pt": "Este comando parece perigoso.",
        "bn": "এই কমান্ডটি বিপজ্জনক মনে হচ্ছে।", "ru": "Эта команда выглядит опасной.",
        "ja": "このコマンドは危険なようです。", "de": "Dieser Befehl scheint gefährlich zu sein.",
        "fr": "Cette commande semble dangereuse.", "tr": "Bu komut tehlikeli görünüyor.",
        "id": "Perintah ini tampaknya berbahaya.", "ko": "이 명령은 위험해 보입니다.", "ur": "یہ کمانڈ خطرناک لگتی ہے۔",
    },
    "This command needs a second look.": {
        "es": "Este comando requiere una segunda revisión.", "zh": "此命令需要再次检查。",
        "hi": "इस कमांड की दोबारा जाँच आवश्यक है।", "ar": "يحتاج هذا الأمر إلى مراجعة إضافية.",
        "pt": "Este comando precisa de uma segunda análise.", "bn": "এই কমান্ডটি আরও একবার দেখা দরকার।",
        "ru": "Эту команду стоит проверить ещё раз.", "ja": "このコマンドは再確認が必要です。",
        "de": "Dieser Befehl sollte noch einmal geprüft werden.", "fr": "Cette commande mérite une seconde vérification.",
        "tr": "Bu komutun yeniden incelenmesi gerekiyor.", "id": "Perintah ini perlu ditinjau kembali.",
        "ko": "이 명령은 한 번 더 확인해야 합니다.", "ur": "اس کمانڈ پر دوبارہ غور کریں۔",
    },
    "Help text — {name}": {
        "es": "Texto de ayuda — {name}", "zh": "帮助文本 — {name}", "hi": "सहायता पाठ — {name}",
        "ar": "نص المساعدة — {name}", "pt": "Texto de ajuda — {name}", "bn": "সহায়তা পাঠ — {name}",
        "ru": "Справка — {name}", "ja": "ヘルプテキスト — {name}", "de": "Hilfetext — {name}",
        "fr": "Texte d’aide — {name}", "tr": "Yardım metni — {name}", "id": "Teks bantuan — {name}",
        "ko": "도움말 — {name}", "ur": "مدد کا متن — {name}",
    },
    "{options} options and {arguments} arguments were read from this text (source: {source}, confidence {confidence}).": {
        "es": "Se leyeron {options} opciones y {arguments} argumentos de este texto (origen: {source}, confianza {confidence}).",
        "zh": "从此文本读取了 {options} 个选项和 {arguments} 个参数（来源：{source}，置信度 {confidence}）。",
        "hi": "इस पाठ से {options} विकल्प और {arguments} आर्ग्युमेंट पढ़े गए (स्रोत: {source}, विश्वास {confidence})।",
        "ar": "تمت قراءة {options} خيارات و{arguments} وسيطات من هذا النص (المصدر: {source}، الثقة {confidence}).",
        "pt": "Foram lidas {options} opções e {arguments} argumentos deste texto (origem: {source}, confiança {confidence}).",
        "bn": "এই পাঠ্য থেকে {options}টি বিকল্প এবং {arguments}টি আর্গুমেন্ট পড়া হয়েছে (উৎস: {source}, নির্ভরযোগ্যতা {confidence})।",
        "ru": "Из этого текста прочитано параметров: {options}, аргументов: {arguments} (источник: {source}, уверенность {confidence}).",
        "ja": "このテキストからオプション {options} 個、引数 {arguments} 個を読み取りました（ソース: {source}、信頼度 {confidence}）。",
        "de": "{options} Optionen und {arguments} Argumente wurden aus diesem Text gelesen (Quelle: {source}, Zuverlässigkeit {confidence}).",
        "fr": "{options} options et {arguments} arguments ont été lus dans ce texte (source : {source}, confiance {confidence}).",
        "tr": "Bu metinden {options} seçenek ve {arguments} bağımsız değişken okundu (kaynak: {source}, güven: {confidence}).",
        "id": "{options} opsi dan {arguments} argumen dibaca dari teks ini (sumber: {source}, keyakinan {confidence}).",
        "ko": "이 텍스트에서 옵션 {options}개와 인수 {arguments}개를 읽었습니다(출처: {source}, 신뢰도 {confidence}).",
        "ur": "اس متن سے {options} اختیارات اور {arguments} آرگومنٹس پڑھے گئے (ماخذ: {source}، اعتماد {confidence})۔",
    },
    "Running…": {
        "es": "Ejecutando…", "zh": "正在运行…", "hi": "चल रहा है…", "ar": "قيد التشغيل…",
        "pt": "Executando…", "bn": "চলছে…", "ru": "Выполняется…", "ja": "実行中…",
        "de": "Wird ausgeführt…", "fr": "En cours…", "tr": "Çalışıyor…", "id": "Berjalan…",
        "ko": "실행 중…", "ur": "چل رہا ہے…",
    },
    "Cancelled": {
        "es": "Cancelado", "zh": "已取消", "hi": "रद्द किया गया", "ar": "أُلغي",
        "pt": "Cancelado", "bn": "বাতিল হয়েছে", "ru": "Отменено", "ja": "キャンセルしました",
        "de": "Abgebrochen", "fr": "Annulé", "tr": "İptal edildi", "id": "Dibatalkan",
        "ko": "취소됨", "ur": "منسوخ",
    },
    "Finished successfully": {
        "es": "Finalizado correctamente", "zh": "成功完成", "hi": "सफलतापूर्वक पूरा हुआ",
        "ar": "اكتمل بنجاح", "pt": "Concluído com sucesso", "bn": "সফলভাবে সম্পন্ন",
        "ru": "Успешно завершено", "ja": "正常に完了しました", "de": "Erfolgreich abgeschlossen",
        "fr": "Terminé avec succès", "tr": "Başarıyla tamamlandı", "id": "Selesai dengan sukses",
        "ko": "성공적으로 완료됨", "ur": "کامیابی سے مکمل",
    },
    "Exited with code {code}": {
        "es": "Finalizó con el código {code}", "zh": "退出代码：{code}", "hi": "कोड {code} के साथ बाहर निकला",
        "ar": "انتهى برمز {code}", "pt": "Saiu com o código {code}", "bn": "কোড {code} দিয়ে শেষ হয়েছে",
        "ru": "Завершено с кодом {code}", "ja": "終了コード {code} で終了しました",
        "de": "Mit Code {code} beendet", "fr": "Terminé avec le code {code}",
        "tr": "{code} koduyla sonlandı", "id": "Keluar dengan kode {code}",
        "ko": "코드 {code}(으)로 종료됨", "ur": "کوڈ {code} کے ساتھ ختم",
    },
    "Cleared {count} cached command(s)": {
        "es": "Se borraron {count} comandos de la caché", "zh": "已清除 {count} 条缓存命令",
        "hi": "{count} कैश किए गए कमांड साफ़ किए गए", "ar": "تم مسح {count} من الأوامر المخزنة مؤقتًا",
        "pt": "{count} comando(s) removido(s) do cache", "bn": "{count}টি ক্যাশ করা কমান্ড মুছে ফেলা হয়েছে",
        "ru": "Удалено из кэша команд: {count}", "ja": "キャッシュされたコマンドを {count} 件消去しました",
        "de": "{count} zwischengespeicherte Befehle gelöscht", "fr": "{count} commande(s) supprimée(s) du cache",
        "tr": "{count} önbelleğe alınmış komut temizlendi", "id": "{count} perintah cache dihapus",
        "ko": "캐시된 명령 {count}개를 지웠습니다", "ur": "{count} کیش شدہ کمانڈز صاف ہوئیں",
    },
    "{count} options": {
        "es": "{count} opciones", "zh": "{count} 个选项", "hi": "{count} विकल्प",
        "ar": "{count} خيارات", "pt": "{count} opções", "bn": "{count}টি বিকল্প",
        "ru": "Параметров: {count}", "ja": "オプション {count} 個", "de": "{count} Optionen",
        "fr": "{count} options", "tr": "{count} seçenek", "id": "{count} opsi",
        "ko": "옵션 {count}개", "ur": "{count} اختیارات",
    },
    "{count} arguments": {
        "es": "{count} argumentos", "zh": "{count} 个参数", "hi": "{count} आर्ग्युमेंट",
        "ar": "{count} وسيطات", "pt": "{count} argumentos", "bn": "{count}টি আর্গুমেন্ট",
        "ru": "Аргументов: {count}", "ja": "引数 {count} 個", "de": "{count} Argumente",
        "fr": "{count} arguments", "tr": "{count} bağımsız değişken", "id": "{count} argumen",
        "ko": "인수 {count}개", "ur": "{count} آرگومنٹس",
    },
    "{count} subcommands": {
        "es": "{count} subcomandos", "zh": "{count} 个子命令", "hi": "{count} सब-कमांड",
        "ar": "{count} أوامر فرعية", "pt": "{count} subcomandos", "bn": "{count}টি সাবকমান্ড",
        "ru": "Подкоманд: {count}", "ja": "サブコマンド {count} 個", "de": "{count} Unterbefehle",
        "fr": "{count} sous-commandes", "tr": "{count} alt komut", "id": "{count} subperintah",
        "ko": "하위 명령 {count}개", "ur": "{count} ذیلی کمانڈز",
    },
    "{command}: {details} (via {origin})": {
        "es": "{command}: {details} (mediante {origin})",
        "zh": "{command}：{details}（通过 {origin}）", "hi": "{command}: {details} ({origin} के माध्यम से)",
        "ar": "{command}: {details} (عبر {origin})", "pt": "{command}: {details} (via {origin})",
        "bn": "{command}: {details} ({origin} এর মাধ্যমে)", "ru": "{command}: {details} (источник: {origin})",
        "ja": "{command}: {details}（{origin} 経由）", "de": "{command}: {details} (über {origin})",
        "fr": "{command} : {details} (via {origin})", "tr": "{command}: {details} ({origin} aracılığıyla)",
        "id": "{command}: {details} (melalui {origin})", "ko": "{command}: {details} ({origin} 사용)",
        "ur": "{command}: {details} ({origin} کے ذریعے)",
    },
    "{name}  …  still required: {missing}": {
        "es": "{name}  …  aún obligatorio: {missing}", "zh": "{name}  …  仍需填写：{missing}",
        "hi": "{name}  …  अभी आवश्यक: {missing}", "ar": "{name}  …  لا يزال مطلوبًا: {missing}",
        "pt": "{name}  …  ainda obrigatório: {missing}", "bn": "{name}  …  এখনও প্রয়োজন: {missing}",
        "ru": "{name}  …  ещё требуется: {missing}", "ja": "{name}  …  必須項目: {missing}",
        "de": "{name}  …  noch erforderlich: {missing}", "fr": "{name}  …  encore requis : {missing}",
        "tr": "{name}  …  hâlâ gerekli: {missing}", "id": "{name}  …  masih wajib: {missing}",
        "ko": "{name}  …  아직 필요함: {missing}", "ur": "{name}  …  ابھی درکار: {missing}",
    },
    "Command not found: {error}": {
        "es": "Comando no encontrado: {error}", "zh": "未找到命令：{error}",
        "hi": "कमांड नहीं मिला: {error}", "ar": "لم يتم العثور على الأمر: {error}",
        "pt": "Comando não encontrado: {error}", "bn": "কমান্ড পাওয়া যায়নি: {error}",
        "ru": "Команда не найдена: {error}", "ja": "コマンドが見つかりません: {error}",
        "de": "Befehl nicht gefunden: {error}", "fr": "Commande introuvable : {error}",
        "tr": "Komut bulunamadı: {error}", "id": "Perintah tidak ditemukan: {error}",
        "ko": "명령을 찾을 수 없음: {error}", "ur": "کمانڈ نہیں ملی: {error}",
    },
    "Close": {
        "es": "Cerrar", "zh": "关闭", "hi": "बंद करें", "ar": "إغلاق", "pt": "Fechar",
        "bn": "বন্ধ", "ru": "Закрыть", "ja": "閉じる", "de": "Schließen", "fr": "Fermer",
        "tr": "Kapat", "id": "Tutup", "ko": "닫기", "ur": "بند کریں",
    },
    "Update required": {
        "es": "Actualización obligatoria", "zh": "需要更新", "hi": "अपडेट आवश्यक है",
        "ar": "التحديث مطلوب", "pt": "Atualização necessária", "bn": "আপডেট প্রয়োজন",
        "ru": "Требуется обновление", "ja": "アップデートが必要です", "de": "Update erforderlich",
        "fr": "Mise à jour requise", "tr": "Güncelleme gerekli", "id": "Pembaruan diperlukan",
        "ko": "업데이트 필요", "ur": "اپ ڈیٹ درکار ہے",
    },
    "Version check required": {
        "es": "Se requiere comprobar la versión", "zh": "需要检查版本", "hi": "संस्करण जाँच आवश्यक है",
        "ar": "يلزم التحقق من الإصدار", "pt": "É necessário verificar a versão",
        "bn": "সংস্করণ পরীক্ষা প্রয়োজন", "ru": "Требуется проверка версии",
        "ja": "バージョンの確認が必要です", "de": "Versionsprüfung erforderlich",
        "fr": "Vérification de version requise", "tr": "Sürüm denetimi gerekli",
        "id": "Pemeriksaan versi diperlukan", "ko": "버전 확인 필요", "ur": "ورژن کی جانچ ضروری ہے",
    },
    "Open App Store": {
        "es": "Abrir App Store", "zh": "打开 App Store", "hi": "App Store खोलें", "ar": "افتح App Store",
        "pt": "Abrir App Store", "bn": "App Store খুলুন", "ru": "Открыть App Store",
        "ja": "App Store を開く", "de": "App Store öffnen", "fr": "Ouvrir l’App Store",
        "tr": "App Store'u aç", "id": "Buka App Store", "ko": "App Store 열기", "ur": "App Store کھولیں",
    },
    "Quit": {
        "es": "Salir", "zh": "退出", "hi": "बाहर निकलें", "ar": "إنهاء", "pt": "Sair",
        "bn": "প্রস্থান", "ru": "Выйти", "ja": "終了", "de": "Beenden", "fr": "Quitter",
        "tr": "Çık", "id": "Keluar", "ko": "종료", "ur": "باہر نکلیں",
    },
    "No help text was captured.": {
        "es": "No se capturó texto de ayuda.", "zh": "未捕获帮助文本。",
        "hi": "कोई सहायता पाठ कैप्चर नहीं हुआ।", "ar": "لم يتم التقاط نص المساعدة.",
        "pt": "Nenhum texto de ajuda foi capturado.", "bn": "কোনো সহায়তা পাঠ পাওয়া যায়নি।",
        "ru": "Текст справки не получен.", "ja": "ヘルプテキストを取得できませんでした。",
        "de": "Es wurde kein Hilfetext erfasst.", "fr": "Aucun texte d’aide n’a été capturé.",
        "tr": "Yardım metni yakalanmadı.", "id": "Teks bantuan tidak ditemukan.",
        "ko": "도움말 텍스트를 가져오지 못했습니다.", "ur": "مدد کا متن حاصل نہیں ہوا۔",
    },
}

_SWEDISH = {
        "Settings": {"sv": "Inställningar"},
        "Appearance": {"sv": "Utseende"},
        "Language": {"sv": "Språk"},
        "Version": {"sv": "Version"},
        "Light": {"sv": "Ljust"},
        "Dark": {"sv": "Mörkt"},
        "Follow system": {"sv": "Följ systemet"},
        "System language": {"sv": "Systemspråk"},
        "Recent commands": {"sv": "Senaste kommandon"},
        "No recent commands": {"sv": "Inga senaste kommandon"},
        "New Session": {"sv": "Ny session"},
        "Start a new command": {"sv": "Starta ett nytt kommando"},
        "Discover": {"sv": "Hitta"},
        "Show help text": {"sv": "Visa hjälptext"},
        "Working directory (defaults to your home)": {
            "sv": "Arbetskatalog (standard är din hemkatalog)"
        },
        "Choose…": {"sv": "Välj…"},
        "Copy": {"sv": "Kopiera"},
        "Run": {"sv": "Kör"},
        "Cancel": {"sv": "Avbryt"},
        "Command Line Interface": {"sv": "Kommandoradsgränssnitt"},
        "Output": {"sv": "Utdata"},
        "Explore CLI commands": {"sv": "Utforska CLI-kommandon"},
        "Clear": {"sv": "Rensa"},
        "Tools": {"sv": "Verktyg"},
        "Arguments": {"sv": "Argument"},
        "Required options": {"sv": "Obligatoriska alternativ"},
        "Options": {"sv": "Alternativ"},
        "Additional arguments": {"sv": "Ytterligare argument"},
        "optional": {"sv": "valfritt"},
        "Command output appears here.": {"sv": "Kommandots utdata visas här."},
        "Enter a command above and press Discover.": {
            "sv": "Ange ett kommando ovan och klicka på Hitta."
        },
        "You can still pass arguments using the field above.": {
            "sv": "Du kan fortfarande ange argument i fältet ovan."
        },
        "Ready": {"sv": "Redo"},
        "Command history cleared": {"sv": "Kommandohistoriken har rensats"},
        "Command copied to the clipboard": {
            "sv": "Kommandot har kopierats till urklipp"
        },
        "Settings saved": {"sv": "Inställningarna har sparats"},
        "Settings…": {"sv": "Inställningar…"},
        "Save": {"sv": "Spara"},
        "Clear command history": {"sv": "Rensa kommandohistorik"},
        "Clear the output below": {"sv": "Rensa utdata nedan"},
        "Command to configure, e.g. rsync, git log, ffmpeg": {
            "sv": "Kommando att konfigurera, t.ex. rsync, git log, ffmpeg"
        },
        "Open a subcommand of the current command": {
            "sv": "Öppna ett underkommando till det aktuella kommandot"
        },
        "Clear discovery cache": {"sv": "Rensa upptäcktscache"},
        "No options were discovered for this command. You can still pass arguments using the field above.": {
            "sv": "Inga alternativ hittades för kommandot. Du kan fortfarande ange argument i fältet ovan."
        },
        "Anything not listed above, e.g. --flag value": {
            "sv": "Annat som inte listas ovan, t.ex. --flag värde"
        },
        "extra": {"sv": "extra"},
        "comma-separated values": {"sv": "kommaseparerade värden"},
        "Choose files or folders": {"sv": "Välj filer eller mappar"},
        "Choose": {"sv": "Välj"},
        "Browse…": {"sv": "Bläddra…"},
        "directory path": {"sv": "sökväg till katalog"},
        "file or directory path": {"sv": "sökväg till fil eller katalog"},
        "Choose a directory": {"sv": "Välj en katalog"},
        "Working directory": {"sv": "Arbetskatalog"},
        "You can type here directly.": {"sv": "Du kan skriva här direkt."},
        "Invalid command: check for unmatched quotes": {
            "sv": "Ogiltigt kommando: kontrollera obalanserade citationstecken"
        },
        "Reading --help…": {"sv": "Läser --help…"},
        "Discovery failed": {"sv": "Det gick inte att hitta kommandot"},
        "Cannot read that command": {"sv": "Det går inte att läsa kommandot"},
        "Could not discover options": {"sv": "Det gick inte att hitta några alternativ"},
        "Could not start": {"sv": "Det gick inte att starta"},
        "Run anyway": {"sv": "Kör ändå"},
        "Type RUN to enable the button": {
            "sv": "Skriv RUN för att aktivera knappen"
        },
        "Review before running": {"sv": "Granska före körning"},
        "This command looks dangerous.": {"sv": "Det här kommandot verkar farligt."},
        "This command needs a second look.": {
            "sv": "Det här kommandot bör granskas en gång till."
        },
        "Help text — {name}": {"sv": "Hjälptext — {name}"},
        "{options} options and {arguments} arguments were read from this text (source: {source}, confidence {confidence}).": {
            "sv": "{options} alternativ och {arguments} argument lästes från texten (källa: {source}, säkerhet {confidence})."
        },
        "Running…": {"sv": "Kör…"},
        "Cancelled": {"sv": "Avbrutet"},
        "Finished successfully": {"sv": "Slutfört utan fel"},
        "Exited with code {code}": {"sv": "Avslutades med kod {code}"},
        "Cleared {count} cached command(s)": {
            "sv": "{count} cachade kommandon har rensats"
        },
        "{count} options": {"sv": "{count} alternativ"},
        "{count} arguments": {"sv": "{count} argument"},
        "{count} subcommands": {"sv": "{count} underkommandon"},
        "{command}: {details} (via {origin})": {
            "sv": "{command}: {details} (via {origin})"
        },
        "{name}  …  still required: {missing}": {
            "sv": "{name}  …  saknas fortfarande: {missing}"
        },
        "Command not found: {error}": {"sv": "Kommandot hittades inte: {error}"},
        "Close": {"sv": "Stäng"},
        "Update required": {"sv": "Uppdatering krävs"},
        "Version check required": {"sv": "Versionskontroll krävs"},
        "Open App Store": {"sv": "Öppna App Store"},
        "Quit": {"sv": "Avsluta"},
        "No help text was captured.": {"sv": "Ingen hjälptext kunde hämtas."},
}
for _key, _translation in _SWEDISH.items():
    _TEXT[_key].update(_translation)

_language = "en"


def system_language() -> str:
    code = QLocale.system().name().split("_", 1)[0].split("-", 1)[0].lower()
    aliases = {"in": "id"}
    code = aliases.get(code, code)
    return code if code in {language for language, _ in LANGUAGES} else "en"


def set_language(language: str) -> None:
    global _language
    _language = system_language() if language == LANGUAGE_SYSTEM else language
    if _language not in {code for code, _ in LANGUAGES}:
        _language = "en"
    if application := QApplication.instance():
        direction = (
            Qt.LayoutDirection.RightToLeft
            if _language in {"ar", "ur"}
            else Qt.LayoutDirection.LeftToRight
        )
        application.setLayoutDirection(direction)


def current_language() -> str:
    return _language


def tr(text: str, **values: object) -> str:
    translated = _TEXT.get(text, {}).get(_language, text)
    return translated.format(**values) if values else translated
