package com.gfontconverter.app

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * Вызовы Python-движка (android_api.py). Все вызовы идут по очереди в одном фоновом
 * потоке (порядок важен для правки штрихов), ответ приходит в главный поток.
 */
object Engine {
    private const val TAG = "GfontEngine"
    private val exec = Executors.newSingleThreadExecutor()
    val main = Handler(Looper.getMainLooper())
    private val mod: PyObject by lazy { Python.getInstance().getModule("android_api") }

    fun callSync(fn: String, vararg args: Any?): JSONObject {
        return try {
            val r = JSONObject(mod.callAttr(fn, *args).toString())
            if (!r.optBoolean("ok", false) && r.has("trace")) Log.e(TAG, "$fn: ${r.optString("trace")}")
            r
        } catch (e: Throwable) {
            Log.e(TAG, "$fn", e)
            JSONObject().put("ok", false).put("error", e.message ?: e.toString())
        }
    }

    fun call(fn: String, vararg args: Any?, cb: (JSONObject) -> Unit) {
        exec.execute {
            val r = callSync(fn, *args)
            main.post { cb(r) }
        }
    }

    /** Выполнить произвольную работу в потоке движка (например, копирование файлов). */
    fun run(work: () -> Unit) = exec.execute(work)
}

/** Прогресс и отмена для длинных операций: Python вызывает onProgress и isCancelled. */
class TaskProgress(private val onUpdate: (Int, Int) -> Unit) {
    @Volatile var cancelled = false

    @Suppress("unused")
    fun onProgress(done: Int, total: Int) {
        Engine.main.post { onUpdate(done, total) }
    }

    @Suppress("unused")
    fun isCancelled(): Boolean = cancelled
}

// ---- разбор штрихов из JSON ----
/** [[x, y], ...] -> FloatArray(x0, y0, x1, y1, …) */
fun JSONArray.toPoly(): FloatArray {
    val out = FloatArray(length() * 2)
    for (i in 0 until length()) {
        val p = getJSONArray(i)
        out[2 * i] = p.getDouble(0).toFloat()
        out[2 * i + 1] = p.getDouble(1).toFloat()
    }
    return out
}

/** [[[x, y], ...], ...] -> список ломаных */
fun JSONArray?.toPolys(): List<FloatArray> {
    if (this == null) return emptyList()
    return (0 until length()).map { getJSONArray(it).toPoly() }
}

fun JSONObject.err(): String = optString("error", "ошибка")
