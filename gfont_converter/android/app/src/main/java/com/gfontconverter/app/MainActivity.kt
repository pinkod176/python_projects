package com.gfontconverter.app

import android.content.pm.PackageInfo
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.LinearLayout
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.fragment.app.Fragment
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.progressindicator.CircularProgressIndicator
import java.io.File

class MainActivity : AppCompatActivity() {
    lateinit var toolbar: MaterialToolbar
    private lateinit var container: FrameLayout
    private lateinit var nav: BottomNavigationView
    private lateinit var loading: LinearLayout
    var version = ""
    var ready = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = vbox()
        toolbar = MaterialToolbar(this)
        toolbar.title = "GfontConverter"
        toolbar.menu.add("О программе").setOnMenuItemClickListener { about(); true }
        root.addView(toolbar, lp())
        container = FrameLayout(this).apply { id = View.generateViewId() }
        root.addView(container, lp(h = 0, weight = 1f))
        nav = BottomNavigationView(this)
        nav.menu.add(0, 1, 0, "Конвертер").setIcon(R.drawable.ic_tab_convert)
        nav.menu.add(0, 2, 1, "Свой почерк").setIcon(R.drawable.ic_tab_draw)
        nav.setOnItemSelectedListener { show(if (it.itemId == 1) "conv" else "draw"); true }
        root.addView(nav, lp())
        loading = vbox(24).apply {
            gravity = Gravity.CENTER
            addView(CircularProgressIndicator(this@MainActivity).apply { isIndeterminate = true })
            addView(text("Запуск Python и библиотек…\nпервый раз это занимает до минуты", 15f).apply {
                gravity = Gravity.CENTER
                setPadding(0, dpi(16), 0, 0)
            })
        }
        container.addView(loading, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        setContentView(root)
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(bars.left, bars.top, bars.right, 0)
            nav.setPadding(0, 0, 0, bars.bottom)
            insets
        }
        nav.visibility = View.GONE
        startEngine(savedInstanceState)
    }

    /** Распаковать resources/ (шаблон, шрифт-образец) и запустить движок. */
    private fun startEngine(saved: Bundle?) {
        Engine.run {
            val res = File(filesDir, "resources")
            val stamp = File(res, ".version")
            val ver = packageVersion()
            if (!stamp.exists() || stamp.readText() != ver) {
                res.deleteRecursively()
                copyAssets("resources", res)
                stamp.writeText(ver)
            }
            val r = Engine.callSync("init", filesDir.absolutePath, res.absolutePath)
            Engine.main.post {
                if (!r.optBoolean("ok")) {
                    info("Ошибка запуска", r.err())
                    return@post
                }
                version = r.optString("version")
                toolbar.title = "GfontConverter $version"
                ready = true
                container.removeView(loading)
                nav.visibility = View.VISIBLE
                val tab = saved?.getString("tab") ?: "conv"
                nav.selectedItemId = if (tab == "conv") 1 else 2
                show(tab)
                if (intent.getBooleanExtra("smoke", false)) Smoke(this).start()
            }
        }
    }

    private fun packageVersion(): String {
        val pi: PackageInfo = packageManager.getPackageInfo(packageName, 0)
        val code = if (Build.VERSION.SDK_INT >= 28) pi.longVersionCode else @Suppress("DEPRECATION") pi.versionCode.toLong()
        return "${pi.versionName}-$code-${pi.lastUpdateTime}"
    }

    private fun copyAssets(path: String, dst: File) {
        val list = assets.list(path) ?: return
        if (list.isEmpty()) {
            dst.parentFile?.mkdirs()
            assets.open(path).use { inp -> dst.outputStream().use { inp.copyTo(it) } }
            return
        }
        dst.mkdirs()
        for (name in list) copyAssets("$path/$name", File(dst, name))
    }

    var current = "conv"

    fun show(tag: String) {
        if (!ready) return
        current = tag
        val fm = supportFragmentManager
        val tr = fm.beginTransaction()
        for (t in listOf("conv", "draw")) {
            var f: Fragment? = fm.findFragmentByTag(t)
            if (t == tag) {
                if (f == null) {
                    f = if (t == "conv") ConverterFragment() else DrawFragment()
                    tr.add(container.id, f, t)
                } else tr.show(f)
            } else if (f != null) tr.hide(f)
        }
        tr.commitNowAllowingStateLoss()
        toolbar.subtitle = if (tag == "conv") "Конвертер шрифтов в .gfont" else "Нарисовать свой почерк"
    }

    fun select(tag: String) {
        nav.selectedItemId = if (tag == "conv") 1 else 2
    }

    fun converter(): ConverterFragment? = supportFragmentManager.findFragmentByTag("conv") as? ConverterFragment
    fun draw(): DrawFragment? = supportFragmentManager.findFragmentByTag("draw") as? DrawFragment

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString("tab", current)
    }

    private fun about() {
        report("GfontConverter $version",
            "Конвертер шрифтов TTF/OTF в .gfont и редактор своего почерка.\n\n" +
                "Движок — тот же, что в версии для Windows (Python внутри приложения): " +
                "скелетизация глифов, порядок штрихов как при письме рукой, сборка по шаблону " +
                "и самопроверка файла.\n\n" +
                "Шрифт-образец шаблона — DejaVu Sans (свободная лицензия Bitstream Vera).",
            "")
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (current == "draw") {
            MaterialAlertDialogBuilder(this).setMessage("Выйти из приложения? Почерк сохранён в черновике.")
                .setPositiveButton("Выйти") { _, _ -> finish() }
                .setNegativeButton("Остаться", null).show()
        } else {
            @Suppress("DEPRECATION")
            super.onBackPressed()
        }
    }
}
