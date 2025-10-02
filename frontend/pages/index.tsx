import Head from 'next/head';
import Link from 'next/link';

import DashboardShell from '@/components/Layout/DashboardShell';
import styles from '@/styles/HomePage.module.css';

export default function HomePage() {
  return (
    <DashboardShell>
      <Head>
        <title>sisacao • Growth Funnel Studio</title>
      </Head>
      <div className={styles.hero}>
        <div className={styles.heroContent}>
          <p className={styles.kicker}>Work in progress</p>
          <h1 className={styles.title}>Growth Funnel Studio</h1>
          <p className={styles.subtitle}>
            Estruture funis, acompanhe KPIs e faça experimentos com confiança.
          </p>
          <Link className={styles.cta} href="/funnels/bff71967-495f-44ae-9896-92183c09eb7f/edit">
            Abrir funil de venda
          </Link>
        </div>
      </div>
    </DashboardShell>
  );
}
