import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-sg-border py-8 px-6">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-6 rounded bg-emerald-DEFAULT flex items-center justify-center">
            <svg
              viewBox="0 0 16 16"
              fill="none"
              className="h-3 w-3 text-sg-base"
            >
              <path
                d="M8 1L14 5V11L8 15L2 11V5L8 1Z"
                fill="currentColor"
              />
            </svg>
          </div>
          <span className="text-sm text-muted-foreground">
            Signal Grid &copy; {new Date().getFullYear()}
          </span>
        </div>

        <div className="flex items-center gap-6">
          <Link
            href="/login"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Войти
          </Link>
          <a
            href="https://t.me/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Telegram
          </a>
          <a
            href="mailto:hello@signalgrid.ru"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Email
          </a>
        </div>
      </div>
    </footer>
  );
}
