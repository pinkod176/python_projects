"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <section className="container-x section-y text-center">
      <p className="eyebrow">Что-то пошло не так</p>
      <h1 className="mt-4 text-h1 font-light">Страница временно недоступна</h1>
      <p className="mx-auto mt-6 max-w-md text-ink-soft">Мы уже знаем о проблеме. Попробуйте обновить страницу.</p>
      <button type="button" onClick={reset} className="btn btn-solid mt-10">Попробовать снова</button>
    </section>
  );
}
