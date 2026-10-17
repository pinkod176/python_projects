// Android-версия GfontConverter: интерфейс на Kotlin, движок — тот же Python-код
// (gfont/, gui/draw_mode/ без Qt, android_api.py), запускается через Chaquopy.
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

val appVersion: String = run {
    val init = rootProject.file("../gfont/__init__.py").readText()
    Regex("__version__ = \"([^\"]+)\"").find(init)?.groupValues?.get(1) ?: "1.0"
}

android {
    namespace = "com.gfontconverter.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.gfontconverter.app"
        minSdk = 24
        targetSdk = 35
        versionName = appVersion
        versionCode = appVersion.split(".").let { it[0].toInt() * 100 + it.getOrElse(1) { "0" }.toInt() }
    }

    // Один постоянный ключ для всех сборок, чтобы новая версия ставилась поверх старой.
    // Это «отладочный» ключ (пароль android), он не секретный и не годится для Google Play.
    signingConfigs {
        create("shared") {
            storeFile = file("gfont-debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        getByName("debug") { signingConfig = signingConfigs.getByName("shared") }
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("shared")
        }
    }

    // phone — телефоны и планшеты (ARM64); emu — эмулятор x86_64 (проверка в CI)
    flavorDimensions += "abi"
    productFlavors {
        create("phone") {
            dimension = "abi"
            ndk { abiFilters += "arm64-v8a" }
        }
        create("emu") {
            dimension = "abi"
            ndk { abiFilters += "x86_64" }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    lint { checkReleaseBuilds = false }

    sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/gfontAssets"))
}

// resources/ настольной версии (встроенный шаблон, шрифт-образец) -> assets/resources.
// Имя шаблона в assets — латиницей; android_api.init возвращает ему исходное имя.
// Сборку запускать с UTF-8 локалью (LANG=C.UTF-8): в имени шаблона кириллица.
val copyGfontResources by tasks.registering(Sync::class) {
    from(rootProject.file("../resources")) {
        include("*.gfont", "sample/**")
        rename { if (it.endsWith(".gfont")) "default_template.gfont" else it }
        into("resources")
    }
    into(layout.buildDirectory.dir("generated/gfontAssets"))
}
tasks.named("preBuild") { dependsOn(copyGfontResources) }

chaquopy {
    defaultConfig {
        version = "3.10"
        System.getenv("CHAQUOPY_BUILD_PYTHON")?.let { buildPython(it) }
        pip {
            // Пакеты ставятся без зависимостей, список полный: scikit-image без
            // необязательных matplotlib, imageio, networkx… (движку нужны skeletonize и
            // find_contours). Тот же набор проверяется тестами в CI.
            options("--no-deps")
            install("numpy==1.23.3")
            install("scipy==1.8.1")
            install("scikit-image==0.18.3")
            install("PyWavelets==1.1.1")
            install("chaquopy-openblas")
            install("chaquopy-libcxx")
            install("chaquopy-libgfortran")
            install("chaquopy-libomp")
            install("fonttools==4.53.1")
            install("pillow==11.0.0")          // растеризация глифов (gfont/extract.py)
            install("chaquopy-freetype")
            install("chaquopy-libjpeg")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("../..")
            include("android_api.py", "gfont/**/*.py", "gui/__init__.py", "gui/draw_mode/__init__.py",
                    "gui/draw_mode/charsets.py", "gui/draw_mode/editor.py", "gui/draw_mode/export.py",
                    "gui/draw_mode/fill.py", "gui/draw_mode/geometry.py", "gui/draw_mode/project.py",
                    "gui/draw_mode/strokes.py", "gui/draw_mode/template_core.py")
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.fragment:fragment-ktx:1.8.5")
}
