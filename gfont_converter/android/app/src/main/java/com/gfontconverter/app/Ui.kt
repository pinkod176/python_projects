package com.gfontconverter.app

import android.content.Context
import android.content.res.Configuration
import android.graphics.Typeface
import android.net.Uri
import android.provider.OpenableColumns
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.slider.Slider
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import java.io.File

// ---------------------------------------------------------------- размеры, тема
fun Context.dp(v: Float): Float = v * resources.displayMetrics.density
fun Context.dpi(v: Int): Int = (v * resources.displayMetrics.density + 0.5f).toInt()
fun Context.isDark(): Boolean =
    (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES

fun lp(w: Int = ViewGroup.LayoutParams.MATCH_PARENT, h: Int = ViewGroup.LayoutParams.WRAP_CONTENT,
       weight: Float = 0f) = LinearLayout.LayoutParams(w, h, weight)

fun Context.vbox(pad: Int = 0): LinearLayout = LinearLayout(this).apply {
    orientation = LinearLayout.VERTICAL
    setPadding(dpi(pad), dpi(pad), dpi(pad), dpi(pad))
}

fun Context.hbox(): LinearLayout = LinearLayout(this).apply {
    orientation = LinearLayout.HORIZONTAL
    gravity = Gravity.CENTER_VERTICAL
}

fun Context.text(s: String, sp: Float = 15f, bold: Boolean = false, alpha: Float = 1f): TextView =
    TextView(this).apply {
        text = s
        textSize = sp
        if (bold) setTypeface(typeface, Typeface.BOLD)
        this.alpha = alpha
    }

fun Context.button(s: String, outlined: Boolean = false, onClick: (View) -> Unit): MaterialButton {
    val b = if (outlined)
        MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle)
    else MaterialButton(this)
    b.text = s
    b.isAllCaps = false
    b.setOnClickListener(onClick)
    return b
}

/** Кнопка панели инструментов: компактная, без заглавных букв. */
fun Context.toolButton(s: String, onClick: (View) -> Unit): MaterialButton =
    button(s, outlined = true, onClick = onClick).apply {
        minWidth = 0
        minimumWidth = 0
        setPadding(dpi(12), 0, dpi(12), 0)
        insetTop = 0
        insetBottom = 0
        minHeight = dpi(44)
        val m = lp(ViewGroup.LayoutParams.WRAP_CONTENT, dpi(44))
        m.marginEnd = dpi(6)
        layoutParams = m
    }

/** Ползунок с подписью и значением. */
class SliderRow(ctx: Context, title: String, from: Float, to: Float, step: Float, value: Float,
                private val fmt: (Float) -> String, onChange: (Float) -> Unit) : LinearLayout(ctx) {
    val slider = Slider(ctx)
    private val valueText = ctx.text("", 14f)

    init {
        orientation = VERTICAL
        val head = ctx.hbox()
        head.addView(ctx.text(title, 14f), lp(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        head.addView(valueText)
        addView(head)
        slider.valueFrom = from
        slider.valueTo = to
        slider.stepSize = step
        slider.value = value.coerceIn(from, to)
        slider.setLabelFormatter { fmt(it) }
        valueText.text = fmt(slider.value)
        slider.addOnChangeListener { _, v, fromUser ->
            valueText.text = fmt(v)
            if (fromUser) onChange(v)
        }
        addView(slider)
    }

    var value: Float
        get() = slider.value
        set(v) {
            slider.value = (Math.round(v / slider.stepSize) * slider.stepSize).coerceIn(slider.valueFrom, slider.valueTo)
            valueText.text = fmt(slider.value)
        }
}

fun Context.textField(hint: String, value: String = "", number: Boolean = false): Pair<TextInputLayout, TextInputEditText> {
    val til = TextInputLayout(this)
    til.hint = hint
    val ed = TextInputEditText(til.context)
    ed.setText(value)
    if (number) ed.inputType = InputType.TYPE_CLASS_NUMBER
    til.addView(ed)
    return til to ed
}

// ---------------------------------------------------------------- диалоги
fun Context.info(title: String, message: String) {
    MaterialAlertDialogBuilder(this).setTitle(title).setMessage(message)
        .setPositiveButton("OK", null).show()
}

/** Отчёт: краткий текст и подробности (прокручиваются). */
fun Context.report(title: String, summary: String, details: String) {
    val box = vbox(20)
    box.addView(text(summary, 15f))
    if (details.isNotBlank()) {
        val d = text(details, 12f, alpha = 0.8f)
        d.typeface = Typeface.MONOSPACE
        d.setTextIsSelectable(true)
        val m = lp()
        m.topMargin = dpi(12)
        box.addView(d, m)
    }
    val sv = ScrollView(this)
    sv.addView(box)
    MaterialAlertDialogBuilder(this).setTitle(title).setView(sv)
        .setPositiveButton("OK", null).show()
}

// ---------------------------------------------------------------- файлы (SAF)
fun Context.displayName(uri: Uri): String {
    var name: String? = null
    try {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) name = c.getString(0)
        }
    } catch (_: Exception) {
    }
    return (name ?: uri.lastPathSegment ?: "file").replace('/', '_')
}

/** Скопировать выбранный пользователем файл в папку приложения (Python работает с путями). */
fun Context.importToCache(uri: Uri, sub: String = "import"): File {
    val dir = File(cacheDir, sub).apply { mkdirs() }
    val out = File(dir, displayName(uri))
    contentResolver.openInputStream(uri)!!.use { inp -> out.outputStream().use { inp.copyTo(it) } }
    return out
}

fun Context.exportFromFile(file: File, uri: Uri) {
    contentResolver.openOutputStream(uri, "wt")!!.use { os -> file.inputStream().use { it.copyTo(os) } }
}
