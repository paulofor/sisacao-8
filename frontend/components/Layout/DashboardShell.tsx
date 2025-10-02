import Link from 'next/link';
import { ReactNode } from 'react';

import styles from '@/styles/DashboardShell.module.css';

type DashboardShellProps = {
  children: ReactNode;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: ReactNode;
};

export default function DashboardShell({ children, breadcrumbs = [], actions }: DashboardShellProps) {
  return (
    <div className={styles.wrapper}>
      <nav className={styles.sidebar} aria-label="Menu principal">
        <div className={styles.brand}>
          <div className={styles.logo}>sisacao</div>
          <p className={styles.brandSubtitle}>Growth Ops</p>
        </div>
        <ul className={styles.menu}>
          <li>
            <Link href="/" className={styles.menuItem}>
              <span aria-hidden>🏠</span>
              <span>Visão geral</span>
            </Link>
          </li>
          <li>
            <Link href="/funnels/bff71967-495f-44ae-9896-92183c09eb7f/edit" className={`${styles.menuItem} ${styles.menuItemActive}`}>
              <span aria-hidden>🧭</span>
              <span>Funis</span>
            </Link>
          </li>
          <li>
            <a className={styles.menuItem} href="#experimentos">
              <span aria-hidden>🧪</span>
              <span>Experimentos</span>
            </a>
          </li>
          <li>
            <a className={styles.menuItem} href="#relatorios">
              <span aria-hidden>📊</span>
              <span>Relatórios</span>
            </a>
          </li>
        </ul>
      </nav>
      <div className={styles.contentArea}>
        <header className={styles.topBar}>
          <div className={styles.breadcrumbs}>
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;

              if (isLast || !crumb.href) {
                return (
                  <span key={crumb.label} className={styles.breadcrumbCurrent}>
                    {crumb.label}
                  </span>
                );
              }

              return (
                <Link key={crumb.label} href={crumb.href} className={styles.breadcrumbLink}>
                  {crumb.label}
                </Link>
              );
            })}
          </div>
          <div className={styles.actions}>{actions}</div>
        </header>
        <main className={styles.main}>{children}</main>
      </div>
    </div>
  );
}
