"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <section className="container-x py-28 text-center">
      <p className="eyebrow">Что-то пошло не так</p>
      <h1 className="mt-4 text-4xl md:text-6xl">Страница временно недоступна</h1>
      <p className="mx-auto mt-5 max-w-md text-ink-soft">Мы уже знаем о проблеме. Попробуйте обновить страницу.</p>
      <button type="button" onClick={reset} className="btn btn-solid mt-8">Попробовать снова</button>
    </section>
  );
}
