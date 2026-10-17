package com.gfontconverter.app

import android.graphics.RectF
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.CheckBox
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.widget.PopupMenu
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.google.android.material.chip.Chip
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.materialswitch.MaterialSwitch
import com.google.android.material.progressindicator.LinearProgressIndicator
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Экран «Свой почерк»: рисование символов по шаблону и сборка .gfont (движок — android_api). */
class DrawFragment : Fragment(), DrawCanvasView.Listener {
    lateinit var canvas: DrawCanvasView
    private lateinit var spGroup: Spinner
    private lateinit var strip: RecyclerView
    private lateinit var tvCounts: TextView
    private lateinit var bar: LinearProgressIndicator
    private lateinit var bUndo: MaterialButton
    private lateinit var bRedo: MaterialButton
    private lateinit var tvWarn: TextView
    private lateinit var chipVar: Chip
    private lateinit var chipEdit: Chip

    private var groups: List<Triple<String, List<Int>, List<String>>> = emptyList()
    private var allCodes: List<Int> = emptyList()
    private var group = 0
    var code = 0x430
    private var variant = 0
    private var nvariants = 1
    private var statuses = JSONObject()
    private val thumbs = mutableMapOf<Int, List<FloatArray>?>()
    private var settings = JSONObject()
    var previewText = "Съешь же ещё этих мягких французских булок, да выпей чаю."
    private var pendingExport: Pair<File, JSONObject>? = null
    private var pendingProjectSave: File? = null
    private var loaded = false
    var lastExport: JSONObject? = null
    private val autosave = object : Runnable {
        override fun run() {
            Engine.call("draw_autosave") { }
            canvas.postDelayed(this, 30_000)
        }
    }

    // ---- файлы ----
    private val openProject = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val f = requireContext().importToCache(uri, "projects")
            Engine.call("draw_open", f.absolutePath) { r -> if (ok(r)) afterProjectLoad(r) }
        }
    }
    private val saveProject = registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        val f = pendingProjectSave ?: return@registerForActivityResult
        if (uri == null) return@registerForActivityResult
        Engine.call("draw_save", f.absolutePath) { r ->
            if (!ok(r)) return@call
            try {
                requireContext().exportFromFile(f, uri)
                toast("Проект сохранён")
            } catch (e: Exception) {
                requireContext().info("Не сохранено", e.message ?: e.toString())
            }
        }
    }
    private val openGfont = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val f = requireContext().importToCache(uri, "gfont")
            Engine.call("draw_import_gfont", f.absolutePath) { r ->
                if (ok(r)) {
                    afterProjectLoad(r)
                    toast("Загружено символов: ${r.optInt("imported")}. Экспорт будет собран поверх этого файла.")
                }
            }
        }
    }
    private val pickSample = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val f = requireContext().importToCache(uri, "samples")
            Engine.call("draw_sample", f.absolutePath) { r ->
                if (ok(r)) { toast("Образец шаблона: ${r.optString("sample")}"); loadTemplate() }
            }
        }
    }
    private var fontPickFit = true
    private val pickFillFont = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) fillFromFont(requireContext().importToCache(uri, "fonts").absolutePath, fontPickFit)
    }
    private val createGfont = registerForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
        val p = pendingExport ?: return@registerForActivityResult
        if (uri != null) export(p.first, p.second) { requireContext().exportFromFile(p.first, uri) }
    }

    // ================================================================ интерфейс
    override fun onCreateView(inflater: LayoutInflater, parent: ViewGroup?, saved: Bundle?): View {
        val ctx = requireContext()
        val root = ctx.vbox(8)

        val head = ctx.hbox()
        spGroup = Spinner(ctx)
        head.addView(spGroup, lp(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        tvCounts = ctx.text("", 13f)
        head.addView(tvCounts)
        root.addView(head)
        bar = LinearProgressIndicator(ctx)
        root.addView(bar, lp().apply { topMargin = ctx.dpi(2); bottomMargin = ctx.dpi(4) })

        strip = RecyclerView(ctx)
        strip.layoutManager = LinearLayoutManager(ctx, LinearLayoutManager.HORIZONTAL, false)
        strip.adapter = StripAdapter()
        root.addView(strip, lp(h = ctx.dpi(64)))

        canvas = DrawCanvasView(ctx)
        canvas.listener = this
        root.addView(canvas, lp(h = 0, weight = 1f).apply { topMargin = ctx.dpi(6) })

        tvWarn = ctx.text("", 12f).apply { setTextColor(0xFFC77700.toInt()); visibility = View.GONE }
        root.addView(tvWarn)

        val r1 = ctx.hbox()
        bUndo = ctx.toolButton("↶ Отменить") { edit("undo") }
        bRedo = ctx.toolButton("↷ Повторить") { edit("redo") }
        r1.addView(bUndo)
        r1.addView(bRedo)
        r1.addView(ctx.toolButton("⌫ штрих") { edit("delete_last") })
        r1.addView(ctx.toolButton("Очистить") { edit("clear") })
        r1.addView(ctx.toolButton("◀ Назад") { step(-1) })
        r1.addView(ctx.toolButton("Пропустить") { skip() })
        r1.addView(ctx.toolButton("Дальше ▶") { step(1) })
        root.addView(HorizontalScrollView(ctx).apply { addView(r1); isHorizontalScrollBarEnabled = false },
            lp().apply { topMargin = ctx.dpi(6) })

        val r2 = ctx.hbox()
        fun chip(s: String, checked: Boolean, f: (Boolean) -> Unit) = Chip(ctx).apply {
            text = s
            isCheckable = true
            isChecked = checked
            setOnCheckedChangeListener { _, on -> f(on) }
            layoutParams = lp(ViewGroup.LayoutParams.WRAP_CONTENT).apply { marginEnd = ctx.dpi(6) }
        }
        r2.addView(chip("Шаблон", true) { canvas.showTemplate = it; setting("show_template", it) })
        r2.addView(chip("Порядок штрихов", false) { on ->
            canvas.showOrder = on; setting("show_order", on); if (on) loadHint() else canvas.invalidate()
        })
        r2.addView(chip("Линии", true) { canvas.showGuides = it; setting("show_guides", it) })
        chipEdit = chip("Правка точек", false) { canvas.editMode = it; canvas.invalidate() }
        r2.addView(chipEdit)
        chipVar = Chip(ctx).apply {
            text = "Вариант 1"
            setOnClickListener { variantMenu(it) }
        }
        r2.addView(chipVar)
        root.addView(HorizontalScrollView(ctx).apply { addView(r2); isHorizontalScrollBarEnabled = false })

        val r3 = ctx.hbox()
        r3.addView(ctx.toolButton("Меню ▾") { menu(it) })
        r3.addView(ctx.toolButton("Настройки") { settingsDialog() })
        r3.addView(ctx.toolButton("Предпросмотр") { previewDialog() })
        r3.addView(ctx.toolButton("Заполнить…") { fillDialog() })
        r3.addView(ctx.button("Экспорт .gfont…") { exportDialog() }.apply {
            insetTop = 0; insetBottom = 0; minHeight = ctx.dpi(44)
        })
        root.addView(HorizontalScrollView(ctx).apply { addView(r3); isHorizontalScrollBarEnabled = false })

        init()
        return root
    }

    private fun ok(r: JSONObject): Boolean {
        if (!r.optBoolean("ok")) {
            if (!r.optBoolean("cancelled")) context?.info("Ошибка", r.err())
            return false
        }
        return true
    }

    private fun toast(s: String) = Toast.makeText(requireContext(), s, Toast.LENGTH_LONG).show()

    // ================================================================ загрузка
    private fun init() {
        Engine.call("draw_init") { r ->
            if (!ok(r)) return@call
            if (r.optBoolean("restored")) toast("Восстановлен черновик прошлого сеанса")
            Engine.call("draw_groups") { g ->
                if (!ok(g)) return@call
                val arr = g.getJSONArray("groups")
                groups = (0 until arr.length()).map { i ->
                    val it = arr.getJSONArray(i)
                    val codes = it.getJSONArray(1)
                    val labels = it.getJSONArray(2)
                    Triple(it.getString(0), (0 until codes.length()).map { codes.getInt(it) },
                        (0 until labels.length()).map { labels.getString(it) })
                }
                allCodes = groups.flatMap { it.second }
                spGroup.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item,
                    groups.map { it.first })
                spGroup.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                    override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                        if (pos != group) { group = pos; loadThumbs(); strip.adapter?.notifyDataSetChanged() }
                    }
                    override fun onNothingSelected(p: AdapterView<*>?) {}
                }
                afterProjectLoad(r)
                loaded = true
                canvas.postDelayed(autosave, 30_000)
            }
        }
    }

    private fun applyState(r: JSONObject) {
        statuses = r.optJSONObject("statuses") ?: JSONObject()
        settings = r.optJSONObject("settings") ?: settings
        val c = r.optJSONArray("counts")
        if (c != null) counts(c)
        canvas.showTemplate = settings.optBoolean("show_template", true)
        canvas.showOrder = settings.optBoolean("show_order", false)
        canvas.showGuides = settings.optBoolean("show_guides", true)
        canvas.opacity = settings.optDouble("template_opacity", 0.35).toFloat()
        canvas.pen = settings.optDouble("pen", 9.0).toFloat()
        previewText = settings.optString("preview_text", previewText)
    }

    private fun counts(c: JSONArray) {
        val user = c.getInt(0)
        val auto = c.getInt(1)
        val total = c.getInt(2)
        tvCounts.text = "нарисовано $user из $total" + if (auto > 0) " (+$auto)" else ""
        bar.max = total
        bar.progress = user + auto
    }

    private fun afterProjectLoad(r: JSONObject) {
        applyState(r)
        Engine.call("draw_geometry") { g ->
            if (!ok(g)) return@call
            canvas.cellW = g.getDouble("width").toFloat()
            canvas.cellH = g.getDouble("height").toFloat()
            canvas.k = g.getDouble("k").toFloat()
            canvas.cap = g.getDouble("cap").toFloat()
            val gs = g.getJSONArray("guides")
            canvas.guides = (0 until gs.length()).map { gs.getJSONArray(it).getString(0) to gs.getJSONArray(it).getDouble(1).toFloat() }
            canvas.fit()
            thumbs.clear()
            loadThumbs()
            val first = allCodes.firstOrNull { statuses.optJSONArray(it.toString())?.optString(0) !in setOf("drawn", "skipped") }
                ?: allCodes.first()
            select(first)
        }
    }

    private fun loadThumbs(codes: List<Int> = groups.getOrNull(group)?.second ?: emptyList()) {
        if (codes.isEmpty()) return
        Engine.call("draw_thumbs", JSONArray(codes).toString()) { r ->
            if (!r.optBoolean("ok")) return@call
            val g = r.getJSONObject("glyphs")
            for (k in g.keys()) thumbs[k.toInt()] = if (g.isNull(k)) null else g.getJSONArray(k).toPolys()
            strip.adapter?.notifyDataSetChanged()
        }
    }

    // ================================================================ символ
    fun select(c: Int, v: Int = 0, then: (() -> Unit)? = null) {
        code = c
        variant = v
        val gi = groups.indexOfFirst { c in it.second }
        if (gi >= 0 && gi != group) {
            group = gi
            spGroup.setSelection(gi)
            loadThumbs()
        }
        strip.adapter?.notifyDataSetChanged()
        val pos = groups.getOrNull(group)?.second?.indexOf(c) ?: -1
        if (pos >= 0) strip.scrollToPosition(pos)
        Engine.call("draw_select", c, v) { r -> if (ok(r)) applyGlyph(r) }
        loadTemplate()
        if (canvas.showOrder) loadHint()
        Engine.run { Engine.main.post { then?.invoke() } }
    }

    private fun loadTemplate() {
        Engine.call("draw_template", code) { t ->
            if (!t.optBoolean("ok")) return@call
            canvas.tplKind = t.optString("kind", "none")
            canvas.tplPolys = t.optJSONArray("polys").toPolys()
            canvas.tplClosed = t.optBoolean("closed", true)
            val rc = t.optJSONArray("rect")
            if (rc != null) canvas.tplRect = RectF(rc.getDouble(0).toFloat(), rc.getDouble(1).toFloat(),
                (rc.getDouble(0) + rc.getDouble(2)).toFloat(), (rc.getDouble(1) + rc.getDouble(3)).toFloat())
            canvas.tplLabel = t.optString("label")
            canvas.invalidate()
        }
    }

    private fun loadHint() {
        Engine.call("draw_hint", code) { h ->
            if (!h.optBoolean("ok")) return@call
            canvas.hintLines = h.optJSONArray("lines").toPolys()
            val d = h.optJSONArray("dots")
            canvas.hintDots = if (d == null) emptyList() else (0 until d.length()).map { d.getBoolean(it) }
            canvas.invalidate()
        }
    }

    private fun applyGlyph(r: JSONObject) {
        canvas.code = r.optInt("code", code)
        canvas.variant = r.optInt("variant", 0)
        canvas.strokes = r.optJSONArray("strokes").toPolys()
        val d = r.optJSONArray("dots")
        canvas.dots = if (d == null) emptyList() else (0 until d.length()).map { d.getBoolean(it) }
        nvariants = r.optInt("nvariants", 1)
        chipVar.text = "Вариант ${variant + 1}" + if (nvariants > 1) " из ${maxOf(nvariants, variant + 1)}" else ""
        bUndo.isEnabled = r.optBoolean("can_undo")
        bRedo.isEnabled = r.optBoolean("can_redo")
        r.optJSONArray("counts")?.let { counts(it) }
        val st = JSONArray().put(r.optString("status")).put(r.optString("source")).put(nvariants)
        statuses.put(code.toString(), st)
        canvas.invalidate()
    }

    private fun refreshThumb(c: Int) = loadThumbs(listOf(c))

    // ---- события холста ----
    override fun onStroke(points: FloatArray, dot: Boolean) {
        val arr = JSONArray()
        var i = 0
        while (i + 1 < points.size) { arr.put(JSONArray().put(points[i].toDouble()).put(points[i + 1].toDouble())); i += 2 }
        Engine.call("draw_add_stroke", arr.toString(), dot) { r -> if (ok(r)) { applyGlyph(r); refreshThumb(code) } }
    }

    override fun onBeginPoint(stroke: Int) {
        Engine.call("draw_edit", "begin_point", stroke, -1, 0.0, 0.0) { r -> if (ok(r)) applyGlyph(r) }
    }

    override fun onMovePoint(stroke: Int, point: Int, x: Float, y: Float, final: Boolean) {
        Engine.call("draw_edit", "move_point", stroke, point, x.toDouble(), y.toDouble()) { r ->
            if (r.optBoolean("ok")) { applyGlyph(r); if (final) refreshThumb(code) }
        }
    }

    override fun onDeleteStroke(stroke: Int) {
        Engine.call("draw_edit", "delete_stroke", stroke, -1, 0.0, 0.0) { r -> if (ok(r)) { applyGlyph(r); refreshThumb(code) } }
    }

    private fun edit(action: String) {
        Engine.call("draw_edit", action, -1, -1, 0.0, 0.0) { r -> if (ok(r)) { applyGlyph(r); refreshThumb(code) } }
    }

    fun step(d: Int) {
        val i = allCodes.indexOf(code)
        val j = (i + d).coerceIn(0, allCodes.size - 1)
        if (j != i) select(allCodes[j])
    }

    private fun skip() {
        Engine.call("draw_skip", code) { r ->
            if (ok(r)) { applyState(r); strip.adapter?.notifyDataSetChanged(); step(1) }
        }
    }

    private fun variantMenu(anchor: View) {
        val pm = PopupMenu(requireContext(), anchor)
        val n = minOf(5, maxOf(nvariants + 1, variant + 1))
        for (i in 0 until n) pm.menu.add(0, i, i, "Вариант ${i + 1}" + if (i >= nvariants) " (новый)" else "")
        pm.setOnMenuItemClickListener { select(code, it.itemId); true }
        pm.show()
    }

    private fun setting(key: String, value: Any) {
        settings.put(key, value)
        Engine.call("draw_settings", JSONObject().put(key, value).toString()) { }
        canvas.invalidate()
    }

    // ================================================================ меню и диалоги
    private fun menu(anchor: View) {
        val pm = PopupMenu(requireContext(), anchor)
        val items = listOf("Новый проект", "Открыть проект…", "Сохранить проект…", "Открыть готовый .gfont…",
            "Шрифт-образец шаблона (TTF/OTF)…", "Свой шаблон-подсказка .gfont…", "Встроенный образец (DejaVu Sans)",
            "Образцы шрифта как заготовка…", "Вписать холст в экран")
        items.forEachIndexed { i, s -> pm.menu.add(0, i, i, s) }
        pm.setOnMenuItemClickListener {
            when (it.itemId) {
                0 -> MaterialAlertDialogBuilder(requireContext()).setMessage("Начать новый проект? Несохранённый почерк пропадёт.")
                    .setPositiveButton("Начать") { _, _ -> Engine.call("draw_new") { r -> if (ok(r)) afterProjectLoad(r) } }
                    .setNegativeButton("Отмена", null).show()
                1 -> openProject.launch(arrayOf("*/*"))
                2 -> {
                    pendingProjectSave = File(requireContext().cacheDir, "out/project.gfproj").apply { parentFile?.mkdirs() }
                    saveProject.launch("Мой почерк.gfproj")
                }
                3 -> openGfont.launch(arrayOf("*/*"))
                4, 5 -> pickSample.launch(arrayOf("*/*"))
                6 -> Engine.call("draw_sample", "") { r -> if (ok(r)) { toast("Образец: ${r.optString("sample")}"); loadTemplate() } }
                7 -> { fontPickFit = false; pickFillFont.launch(arrayOf("*/*")) }
                8 -> canvas.fit()
            }
            true
        }
        pm.show()
    }

    private fun settingsDialog() {
        val ctx = requireContext()
        val box = ctx.vbox(20)
        val changes = JSONObject()
        fun row(title: String, key: String, from: Float, to: Float, step: Float, scale: Float, fmt: (Float) -> String) {
            val v = settings.optDouble(key, from.toDouble() / scale).toFloat() * scale
            box.addView(SliderRow(ctx, title, from, to, step, v, fmt) { changes.put(key, (it / scale).toDouble()) })
        }
        row("Сглаживание", "smoothing", 0f, 100f, 5f, 100f) { "%.0f %%".format(it) }
        row("Плотность точек", "density", 50f, 200f, 10f, 100f) { "%.0f %%".format(it) }
        row("Размер шаблона (разметки)", "size", 80f, 120f, 5f, 100f) { "%.0f %%".format(it) }
        row("Видимость шаблона", "template_opacity", 5f, 100f, 5f, 100f) { "%.0f %%".format(it) }
        row("Толщина пера", "pen", 1f, 30f, 1f, 1f) { "%.0f".format(it) }
        val sw = MaterialSwitch(ctx).apply {
            text = "Автовыравнивание по базовой линии"
            isChecked = settings.optBoolean("autoalign", false)
            setOnCheckedChangeListener { _, on -> changes.put("autoalign", on) }
        }
        box.addView(sw)
        box.addView(ctx.text("«Размер шаблона» меняет разметку холста вместе с шаблоном: рисовать крупнее или " +
            "мельче. Размер букв в файле от него не зависит.", 12f, alpha = 0.7f))
        MaterialAlertDialogBuilder(ctx).setTitle("Настройки").setView(ScrollView(ctx).apply { addView(box) })
            .setPositiveButton("Готово") { _, _ ->
                if (changes.length() == 0) return@setPositiveButton
                Engine.call("draw_settings", changes.toString()) { r ->
                    if (ok(r)) { applyState(r); afterProjectLoadKeep() }
                }
            }.setNegativeButton("Отмена", null).show()
    }

    /** После смены настроек: разметка, миниатюры и текущий символ заново (символ тот же). */
    private fun afterProjectLoadKeep() {
        val keep = code to variant
        Engine.call("draw_geometry") { g ->
            if (!ok(g)) return@call
            canvas.cap = g.getDouble("cap").toFloat()
            canvas.k = g.getDouble("k").toFloat()
            val gs = g.getJSONArray("guides")
            canvas.guides = (0 until gs.length()).map { gs.getJSONArray(it).getString(0) to gs.getJSONArray(it).getDouble(1).toFloat() }
            thumbs.clear()
            loadThumbs()
            select(keep.first, keep.second)
        }
    }

    fun previewDialog() {
        val ctx = requireContext()
        val box = ctx.vbox(16)
        val (til, ed) = ctx.textField("Проверочный текст", previewText)
        box.addView(til)
        val one = StrokeLineView(ctx)
        val line = StrokeLineView(ctx)
        val warn = ctx.text("", 12f).apply { setTextColor(0xFFC77700.toInt()) }
        box.addView(ctx.text("Символ «${String(Character.toChars(code))}» в реальном размере:", 13f))
        box.addView(one)
        box.addView(ctx.text("Строка (бледные буквы ещё не нарисованы):", 13f).apply { setPadding(0, ctx.dpi(8), 0, 0) })
        box.addView(line)
        box.addView(warn)
        val pen = settings.optDouble("pen", 9.0).toFloat()
        one.pen = pen
        line.pen = pen
        fun update() {
            val t = ed.text?.toString() ?: ""
            previewText = t
            val ch = String(Character.toChars(code))
            Engine.call("draw_line", "$t $ch") { r ->
                if (!r.optBoolean("ok")) return@call
                val g = r.getJSONObject("glyphs")
                val map = mutableMapOf<String, List<FloatArray>?>()
                for (k in g.keys()) map[k] = if (g.isNull(k)) null else g.getJSONArray(k).toPolys()
                line.set(t, map)
                one.set(ch, map)
                val w = r.optString("warning")
                warn.text = if (w.isNotEmpty()) "⚠ $w" else ""
            }
        }
        ed.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: android.text.Editable?) { update() }
        })
        update()
        MaterialAlertDialogBuilder(ctx).setTitle("Предпросмотр").setView(ScrollView(ctx).apply { addView(box) })
            .setPositiveButton("Закрыть") { _, _ -> setting("preview_text", previewText) }.show()
    }

    // ---- заполнение ----
    private fun fillDialog() {
        val ctx = requireContext()
        val opts = arrayOf("А. Взять из шрифта TTF/OTF… (размер под ваш почерк)",
            "Б. Повторить из похожих (ё = е + точки, й = и + дужка, № = N + o, ‑ – — из дефиса, а↔a …)",
            "В. Оставить пустыми")
        MaterialAlertDialogBuilder(ctx).setTitle("Заполнить недостающие символы").setItems(opts) { _, which ->
            when (which) {
                0 -> { fontPickFit = true; pickFillFont.launch(arrayOf("*/*")) }
                1 -> Engine.call("draw_fill_similar") { r -> if (ok(r)) review(r.getJSONObject("candidates"), "Из похожих") }
            }
        }.show()
    }

    private fun fillFromFont(path: String, fit: Boolean) {
        val ctx = requireContext()
        val pi = LinearProgressIndicator(ctx).apply { isIndeterminate = true }
        val tp = TaskProgress { d, t -> pi.isIndeterminate = false; pi.max = t; pi.progress = d }
        val dlg = MaterialAlertDialogBuilder(ctx).setTitle("Буквы из шрифта…")
            .setView(ctx.vbox(24).apply { addView(pi) })
            .setNegativeButton("Отмена") { _, _ -> tp.cancelled = true }.setCancelable(false).show()
        Engine.call("draw_fill_font", path, fit, tp) { r ->
            dlg.dismiss()
            if (ok(r)) review(r.getJSONObject("candidates"), if (fit) "Из шрифта" else "Заготовка из шрифта")
        }
    }

    fun review(cands: JSONObject, title: String, autoApply: Boolean = false, then: (() -> Unit)? = null) {
        val ctx = requireContext()
        if (cands.length() == 0) {
            if (!autoApply) ctx.info(title, "Подходящих символов не нашлось. Нарисуйте, например, «-», «е», «и», «N», «o».")
            then?.invoke()
            return
        }
        val items = cands.keys().asSequence().map { it.toInt() }.toList()
        val checked = items.toMutableSet()
        fun apply() {
            Engine.call("draw_apply", JSONArray(checked.toList()).toString()) { r ->
                if (ok(r)) {
                    applyState(r)
                    thumbs.clear()
                    loadThumbs()
                    select(code, variant)
                    toast("Заполнено символов: ${r.optInt("applied")}")
                }
                then?.invoke()
            }
        }
        if (autoApply) { apply(); return }
        val rv = RecyclerView(ctx)
        rv.layoutManager = GridLayoutManager(ctx, 3)
        rv.adapter = object : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
            override fun getItemCount() = items.size
            override fun onCreateViewHolder(p: ViewGroup, t: Int): RecyclerView.ViewHolder {
                val cell = ctx.vbox(4).apply { gravity = Gravity.CENTER_HORIZONTAL }
                cell.addView(GlyphThumbView(ctx), LinearLayout.LayoutParams(ctx.dpi(64), ctx.dpi(64)))
                cell.addView(CheckBox(ctx))
                cell.addView(ctx.text("", 11f, alpha = 0.8f).apply { gravity = Gravity.CENTER; maxLines = 3 })
                return object : RecyclerView.ViewHolder(cell) {}
            }
            override fun onBindViewHolder(h: RecyclerView.ViewHolder, pos: Int) {
                val c = items[pos]
                val cell = h.itemView as LinearLayout
                val tv = cell.getChildAt(0) as GlyphThumbView
                val o = cands.getJSONObject(c.toString())
                tv.ch = String(Character.toChars(c))
                tv.strokes = o.getJSONArray("strokes").toPolys()
                tv.invalidate()
                val cb = cell.getChildAt(1) as CheckBox
                cb.setOnCheckedChangeListener(null)
                cb.isChecked = c in checked
                cb.text = tv.ch
                cb.setOnCheckedChangeListener { _, on -> if (on) checked += c else checked -= c }
                (cell.getChildAt(2) as TextView).text = o.optString("how")
            }
        }
        val box = ctx.vbox(12)
        box.addView(ctx.text("Предлагается заполнить: ${items.size}. Снимите галочки с ненужных.", 13f))
        box.addView(rv, lp(h = ctx.dpi(420)))
        MaterialAlertDialogBuilder(ctx).setTitle(title).setView(box)
            .setPositiveButton("Применить отмеченные") { _, _ -> apply() }
            .setNegativeButton("Отмена", null).show()
    }

    // ---- экспорт ----
    private fun exportDialog() {
        val ctx = requireContext()
        val box = ctx.vbox(20)
        val c = tvCounts.text
        box.addView(ctx.text("Символы: $c", 14f))
        val swOld = MaterialSwitch(ctx).apply {
            text = "Убрать из шаблона буквы старого стиля, которых нет в проекте"
            isChecked = settings.optBoolean("remove_old", true)
        }
        box.addView(swOld)
        val rg = RadioGroup(ctx)
        val rbKeep = RadioButton(ctx).apply { text = "Размеры как нарисованы"; id = View.generateViewId() }
        val rbNorm = RadioButton(ctx).apply { text = "Нормализовать размеры (строчные к одной высоте, заглавные к одной)"; id = View.generateViewId() }
        rg.addView(rbKeep)
        rg.addView(rbNorm)
        rg.check(if (settings.optBoolean("normalize")) rbNorm.id else rbKeep.id)
        box.addView(rg)
        val swAlt = MaterialSwitch(ctx).apply {
            text = "Записать варианты в коды «код + 32768»"
            isChecked = settings.optString("alt_mode") == "plus32768"
        }
        box.addView(swAlt)
        box.addView(ctx.text("⚠ В эталонных файлах коды ≥ 32768 — иероглифы («а» + 32768 = «萰»), а не " +
            "альтернативы. Включайте, только если точно знаете, что приложение берёт варианты оттуда.", 12f).apply {
            setTextColor(0xFFB36B00.toInt())
        })
        val (tilName, edName) = ctx.textField("Имя файла", "Мой почерк.gfont")
        box.addView(tilName)
        MaterialAlertDialogBuilder(ctx).setTitle("Экспорт в .gfont").setView(ScrollView(ctx).apply { addView(box) })
            .setPositiveButton("Экспортировать") { _, _ ->
                var name = edName.text?.toString()?.trim().orEmpty().ifEmpty { "Мой почерк.gfont" }
                if (!name.lowercase().endsWith(".gfont")) name += ".gfont"
                val opts = JSONObject().put("remove_old", swOld.isChecked).put("normalize", rbNorm.isChecked)
                    .put("alt_mode", if (swAlt.isChecked) "plus32768" else "none")
                val f = File(ctx.cacheDir, "out/$name").apply { parentFile?.mkdirs() }
                pendingExport = f to opts
                createGfont.launch(name)
            }.setNegativeButton("Отмена", null).show()
    }

    fun export(out: File, opts: JSONObject, after: (() -> Unit)?) {
        val ctx = requireContext()
        val pi = LinearProgressIndicator(ctx).apply { isIndeterminate = true }
        val tp = TaskProgress { d, t -> pi.isIndeterminate = false; pi.max = t; pi.progress = d }
        val dlg = MaterialAlertDialogBuilder(ctx).setTitle("Экспорт…").setView(ctx.vbox(24).apply { addView(pi) })
            .setNegativeButton("Отмена") { _, _ -> tp.cancelled = true }.setCancelable(false).show()
        Engine.call("draw_export", out.absolutePath, opts.toString(), tp) { r ->
            dlg.dismiss()
            lastExport = r
            if (!ok(r)) return@call
            try {
                after?.invoke()
            } catch (e: Exception) {
                ctx.info("Не удалось записать файл", e.message ?: e.toString())
                return@call
            }
            if (opts.optBoolean("smoke")) return@call
            val valid = r.optBoolean("valid")
            ctx.report(if (valid) "Файл сохранён и проверен" else "Проверка нашла ошибки",
                "Нарисовано вами: ${r.optInt("by_user")}\nЗаполнено автоматически: ${r.optInt("auto")}\n" +
                    "Нет: ${r.optInt("missing")} ${r.optString("missing_chars")}",
                r.optString("text"))
        }
    }

    override fun onPause() {
        super.onPause()
        if (loaded) {
            settings.put("preview_text", previewText)
            Engine.call("draw_autosave") { }
        }
    }

    override fun onDestroyView() {
        canvas.removeCallbacks(autosave)
        super.onDestroyView()
    }

    // ================================================================ лента символов
    private inner class StripAdapter : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
        override fun getItemCount() = groups.getOrNull(group)?.second?.size ?: 0
        override fun onCreateViewHolder(p: ViewGroup, t: Int): RecyclerView.ViewHolder {
            val ctx = p.context
            val v = GlyphThumbView(ctx)
            v.layoutParams = RecyclerView.LayoutParams(ctx.dpi(58), ctx.dpi(58)).apply { marginEnd = ctx.dpi(4) }
            return object : RecyclerView.ViewHolder(v) {}
        }
        override fun onBindViewHolder(h: RecyclerView.ViewHolder, pos: Int) {
            val c = groups[group].second[pos]
            val v = h.itemView as GlyphThumbView
            v.ch = String(Character.toChars(c))
            v.strokes = thumbs[c]
            val st = statuses.optJSONArray(c.toString())
            v.status = st?.optString(0) ?: "empty"
            v.auto = st?.optString(1) in setOf("font", "similar")
            v.current = c == code
            v.contentDescription = groups[group].third[pos]
            v.setOnClickListener { select(c) }
            v.invalidate()
        }
    }
}
