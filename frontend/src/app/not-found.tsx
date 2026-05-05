export default function NotFound() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16 text-slate-900">
      <div className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
        <p className="text-sm font-medium text-brand-700">404</p>
        <h1 className="mt-2 text-2xl font-bold text-slate-950">Page not found</h1>
        <p className="mt-3 text-sm text-slate-600">
          The page you requested does not exist or may have moved.
        </p>
      </div>
    </main>
  );
}
