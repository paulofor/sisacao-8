import styles from '@/styles/MetricSummaryCard.module.css';

type MetricSummaryCardProps = {
  label: string;
  value: string;
  trendLabel: string;
  trendValue: string;
  trendDirection: 'up' | 'down' | 'flat';
};

export default function MetricSummaryCard({ label, value, trendLabel, trendValue, trendDirection }: MetricSummaryCardProps) {
  return (
    <div className={styles.card}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
      <div className={styles.trend} data-direction={trendDirection}>
        <span className={styles.trendValue}>{trendValue}</span>
        <span className={styles.trendLabel}>{trendLabel}</span>
      </div>
    </div>
  );
}
