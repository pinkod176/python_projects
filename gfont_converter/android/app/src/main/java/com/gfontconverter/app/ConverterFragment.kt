package com.gfontconverter.app

import android.content.Context
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import com.google.android.material.button.MaterialButton
import com.google.android.material.materialswitch.MaterialSwitch
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import org.json.JSONObject
import java.io.File

/** Экран «Конвертер»: шрифт TTF/OTF -> .gfont (тот же движок и параметры, что в окне Windows). */
class ConverterFragment : Fragment() {
    private val prefs by lazy { requireContext().getSharedPreferences("gfont", Context.MODE_PRIVATE) }
    private var params = JSONObject()
    private var family = ""
    private var fontPath: String? = null
    private var templatePath = ""
    private var presets: List<Pair<String, String>> = emptyList()
    private var task: TaskProgress? = null
    private var pendingOut: File? = null

    private lateinit var tvFont: TextView
    private lateinit var tvCoverage: TextView
    private lateinit var spCharset: Spinner
    private lateinit var tilCustom: TextInputLayout
    private lateinit var edCustom: TextInputEditText
    private lateinit var spMode: Spinner
    private lateinit var tvTemplate: TextView
    private lateinit var edText: TextInputEditText
    lateinit var line: StrokeLineView
    private lateinit var btnSave: MaterialButton
    private lateinit var btnCancel: MaterialButton
    private lateinit var progress: LinearProgressIndicator
    private lateinit var tvStatus: TextView
    private val sliders = mutableMapOf<String, SliderRow>()
    private val switches = mutableMapOf<String, MaterialSwitch>()
    private val refresh = Runnable { preview() }
    private var applying = false

    private val pickFont = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) loadFont(requireContext().importToCache(uri, "fonts").absolutePath)
    }
    private val pickTemplate = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val f = requireContext().importToCache(uri, "templates")
            if (!f.name.lowercase().endsWith(".gfont")) {
                requireContext().info("Шаблон", "Нужен файл .gfont")
                return@registerForActivityResult
            }
            templatePath = f.absolutePath
            prefs.edit().putString("template", templatePath).apply()
            updateTemplate()
        }
    }
    private val createOut = registerForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
        val f = pendingOut
        if (uri != null && f != null) startSave(f) { requireContext().exportFromFile(f, uri) }
    }

    override fun onCreateView(inflater: LayoutInflater, parent: ViewGroup?, saved: Bundle?): View {
        val ctx = requireContext()
        val sv = ScrollView(ctx)
        val box = ctx.vbox(16)
        sv.addView(box)

        val top = ctx.hbox()
        top.addView(ctx.button("Открыть шрифт…") { pickFont.launch(arrayOf("*/*")) })
        tvFont = ctx.text("Шрифт не выбран", 15f, bold = true).apply { setPadding(ctx.dpi(12), 0, 0, 0) }
        top.addView(tvFont, lp(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        box.addView(top)
        tvCoverage = ctx.text("Откройте TTF, OTF или WOFF (из «Файлов», загрузок, облака)", 13f, alpha = 0.7f)
        box.addView(tvCoverage)

        box.addView(section(ctx, "Набор символов"))
        spCharset = Spinner(ctx)
        box.addView(spCharset)
        val (til, ed) = ctx.textField("Свой набор: впишите символы, например АБВабв№")
        tilCustom = til
        edCustom = ed
        box.addView(til)
        box.addView(section(ctx, "Режим"))
        spMode = Spinner(ctx)
        spMode.adapter = ArrayAdapter(ctx, android.R.layout.simple_spinner_dropdown_item,
            listOf("Центральная линия (скелет)", "Контур", "Авто"))
        box.addView(spMode)

        box.addView(section(ctx, "Параметры"))
        addSlider(box, "slant", "Наклон", -30f, 30f, 1f) { "%+.0f°".format(it) }
        addSlider(box, "scale", "Масштаб", 0.5f, 2f, 0.05f) { "%.0f %%".format(it * 100) }
        addSlider(box, "spacing", "Интервал (ширина)", 0.5f, 2f, 0.05f) { "%.0f %%".format(it * 100) }
        addSlider(box, "density", "Плотность точек", 0.5f, 2f, 0.05f) { "%.0f %%".format(it * 100) }
        addSlider(box, "smooth", "Сглаживание", 0f, 10f, 0.5f) { "%.1f".format(it) }
        addSlider(box, "overhang", "Хвосты строчных", 0f, 1f, 0.05f) { "%.0f %%".format(it * 100) }
        addSlider(box, "liveliness", "Живость почерка", 0f, 1f, 0.05f) { "%.0f %%".format(it * 100) }
        addSwitch(box, "hand_order", "Порядок штрихов как при письме рукой")
        addSwitch(box, "replace_old", "Удалять буквы шаблона, которых нет в шрифте (строго один почерк)")
        addSwitch(box, "no_new_entries", "Не добавлять новые символы, только заменять существующие")

        box.addView(section(ctx, "Шаблон .gfont"))
        val trow = ctx.hbox()
        tvTemplate = ctx.text("", 14f)
        trow.addView(tvTemplate, lp(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        trow.addView(ctx.button("Выбрать", outlined = true) { pickTemplate.launch(arrayOf("*/*")) })
        trow.addView(ctx.button("Встроенный", outlined = true) {
            templatePath = ""
            prefs.edit().putString("template", "").apply()
            updateTemplate()
        })
        box.addView(trow)

        box.addView(section(ctx, "Предпросмотр (по штрихам, как будет в файле)"))
        val (tilT, edT) = ctx.textField("Текст для проверки")
        edText = edT
        box.addView(tilT)
        line = StrokeLineView(ctx)
        box.addView(line, lp())
        val pen = SliderRow(ctx, "Толщина пера (только для просмотра)", 1f, 30f, 1f, 9f, { "%.0f".format(it) }) {
            line.pen = it; line.invalidate()
        }
        box.addView(pen)

        btnSave = ctx.button("Сохранить как .gfont…") { saveDialog() }
        btnSave.isEnabled = false
        box.addView(btnSave, lp().apply { topMargin = ctx.dpi(12) })
        progress = LinearProgressIndicator(ctx).apply { visibility = View.GONE }
        box.addView(progress)
        btnCancel = ctx.button("Отмена", outlined = true) { task?.cancelled = true }
        btnCancel.visibility = View.GONE
        box.addView(btnCancel)
        tvStatus = ctx.text("", 13f, alpha = 0.8f)
        box.addView(tvStatus)

        load(saved)
        return sv
    }

    private fun section(ctx: Context, s: String) = ctx.text(s, 16f, bold = true).apply {
        setPadding(0, ctx.dpi(16), 0, ctx.dpi(4))
    }

    private fun addSlider(box: LinearLayout, key: String, title: String, from: Float, to: Float, step: Float,
                          fmt: (Float) -> String) {
        val r = SliderRow(requireContext(), title, from, to, step, from, fmt) { v ->
            params.put(key, v.toDouble()); changed()
        }
        sliders[key] = r
        box.addView(r)
    }

    private fun addSwitch(box: LinearLayout, key: String, title: String) {
        val sw = MaterialSwitch(requireContext())
        sw.text = title
        sw.setOnCheckedChangeListener { _, on -> if (!applying) { params.put(key, on); changed() } }
        switches[key] = sw
        box.addView(sw)
    }

    private fun load(saved: Bundle?) {
        templatePath = prefs.getString("template", "") ?: ""
        updateTemplate()
        Engine.call("conv_presets") { r ->
            if (!r.optBoolean("ok")) return@call
            val p = r.getJSONArray("presets")
            presets = (0 until p.length()).map { p.getJSONArray(it).getString(0) to p.getJSONArray(it).getString(1) }
            params = JSONObject(r.getJSONObject("defaults").toString())
            prefs.getString("params", null)?.let { s ->
                val old = JSONObject(s)
                for (k in old.keys()) params.put(k, old.get(k))
            }
            spCharset.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item,
                presets.map { it.second })
            applyParams()
            edText.setText(prefs.getString("text", r.optString("preview_text")))
            hookInputs()
            prefs.getString("font", null)?.let { if (File(it).exists()) loadFont(it) }
        }
    }

    private fun applyParams() {
        applying = true
        for ((k, s) in sliders) s.value = params.optDouble(k, s.value.toDouble()).toFloat()
        for ((k, sw) in switches) sw.isChecked = params.optBoolean(k, false)
        val i = presets.indexOfFirst { it.first == params.optString("charset_preset") }
        if (i >= 0) spCharset.setSelection(i)
        spMode.setSelection(listOf("skeleton", "outline", "auto").indexOf(params.optString("mode", "skeleton")).coerceAtLeast(0))
        edCustom.setText(params.optString("custom_chars"))
        tilCustom.visibility = if (params.optString("charset_preset") == "custom") View.VISIBLE else View.GONE
        applying = false
    }

    private fun hookInputs() {
        spCharset.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                if (applying) return
                params.put("charset_preset", presets[pos].first)
                tilCustom.visibility = if (presets[pos].first == "custom") View.VISIBLE else View.GONE
                changed()
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        spMode.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                if (applying) return
                params.put("mode", listOf("skeleton", "outline", "auto")[pos]); changed()
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        edCustom.addTextChangedListener(watcher { params.put("custom_chars", it); changed() })
        edText.addTextChangedListener(watcher { prefs.edit().putString("text", it).apply(); schedule() })
    }

    private fun watcher(f: (String) -> Unit) = object : TextWatcher {
        override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
        override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
        override fun afterTextChanged(s: Editable?) { if (!applying) f(s?.toString() ?: "") }
    }

    private fun changed() {
        prefs.edit().putString("params", params.toString()).apply()
        schedule()
        coverage()
    }

    private fun schedule() {
        line.removeCallbacks(refresh)
        line.postDelayed(refresh, 300)
    }

    private fun updateTemplate() {
        tvTemplate.text = if (templatePath.isEmpty()) "встроенный (с_клода_дополненный)" else File(templatePath).name
    }

    fun loadFont(path: String, then: (() -> Unit)? = null) {
        tvStatus.text = "Открываю шрифт…"
        Engine.call("conv_open_font", path) { r ->
            if (!r.optBoolean("ok")) {
                tvStatus.text = ""
                requireContext().info("Шрифт не открылся", r.err())
                return@call
            }
            fontPath = path
            family = r.optString("family")
            prefs.edit().putString("font", path).apply()
            tvFont.text = family
            tvStatus.text = "Символов в шрифте: ${r.optInt("glyphs")}"
            btnSave.isEnabled = true
            coverage()
            preview(then)
        }
    }

    private fun coverage() {
        if (fontPath == null) return
        Engine.call("conv_coverage", params.toString()) { r ->
            if (r.optBoolean("ok")) {
                val miss = r.optString("missing")
                tvCoverage.text = "В шрифте есть ${r.optInt("have")} из ${r.optInt("total")} символов набора" +
                    if (miss.isNotEmpty()) "; нет: $miss" else ""
            }
        }
    }

    fun preview(then: (() -> Unit)? = null) {
        if (fontPath == null) return
        val t = edText.text?.toString() ?: ""
        Engine.call("conv_preview", t, params.toString()) { r ->
            if (!r.optBoolean("ok")) { tvStatus.text = r.err(); return@call }
            val g = r.getJSONObject("glyphs")
            val map = mutableMapOf<String, List<FloatArray>?>()
            for (k in g.keys()) map[k] = g.getJSONArray(k).toPolys()
            line.set(t, map)
            then?.invoke()
        }
    }

    private fun saveDialog() {
        val name = (family.ifBlank { "font" }).replace(Regex("[\\\\/:*?\"<>|]"), "_") + "_1.gfont"
        pendingOut = File(requireContext().cacheDir, "out/$name").apply { parentFile?.mkdirs() }
        createOut.launch(name)
    }

    /** Сохранение в фоне; after — что сделать с готовым файлом (скопировать в выбранное место). */
    fun startSave(out: File, after: (() -> Unit)?) {
        val tp = TaskProgress { d, t -> progress.isIndeterminate = false; progress.max = t; progress.progress = d }
        task = tp
        progress.isIndeterminate = true
        progress.visibility = View.VISIBLE
        btnCancel.visibility = View.VISIBLE
        btnSave.isEnabled = false
        tvStatus.text = "Сохранение…"
        Engine.call("conv_save", out.absolutePath, params.toString(), templatePath, tp) { r ->
            progress.visibility = View.GONE
            btnCancel.visibility = View.GONE
            btnSave.isEnabled = true
            task = null
            if (!r.optBoolean("ok")) {
                tvStatus.text = r.err()
                if (!r.optBoolean("cancelled")) requireContext().info("Не сохранено", r.err())
                return@call
            }
            try {
                after?.invoke()
            } catch (e: Exception) {
                requireContext().info("Не удалось записать файл", e.message ?: e.toString())
                return@call
            }
            val ok = r.optBoolean("valid")
            tvStatus.text = if (ok) "Готово: ${out.name} — самопроверка OK" else "Сохранено, но проверка нашла ошибки"
            lastReport = r.optString("report")
            lastValid = ok
            if (!isSmoke) requireContext().report(if (ok) "Сохранено" else "Проверка не пройдена",
                "Заменено: ${r.optInt("replaced")}, новых: ${r.optInt("new")}, нет в шрифте: ${r.optInt("missing")}.",
                r.optString("report"))
        }
    }

    var lastReport = ""
    var lastValid = false
    var isSmoke = false
}
