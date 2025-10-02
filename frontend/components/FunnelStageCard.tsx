import clsx from 'clsx';
import { ChangeEvent, CSSProperties } from 'react';

import styles from '@/styles/FunnelStageCard.module.css';

export type FunnelStage = {
  id: string;
  title: string;
  personaFocus: string;
  targetConversion: number;
  avgVelocityDays: number;
  owner: string;
  automations: string[];
  notes: string;
  touchpoints: string[];
  healthScore: number;
};

type FunnelStageCardProps = {
  stage: FunnelStage;
  index: number;
  total: number;
  accentColor: string;
  isActive: boolean;
  onSelect: (stageId: string) => void;
  onStageChange: (stageId: string, patch: Partial<FunnelStage>) => void;
};

export default function FunnelStageCard({
  stage,
  index,
  total,
  accentColor,
  isActive,
  onSelect,
  onStageChange
}: FunnelStageCardProps) {
  const handleInputChange = (field: keyof FunnelStage) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const value = event.target.type === 'number' ? Number(event.target.value) : event.target.value;
    onStageChange(stage.id, { [field]: value } as Partial<FunnelStage>);
  };

  const handleConversionChange = (event: ChangeEvent<HTMLInputElement>) => {
    onStageChange(stage.id, { targetConversion: Number(event.target.value) });
  };

  const handleVelocityChange = (event: ChangeEvent<HTMLInputElement>) => {
    onStageChange(stage.id, { avgVelocityDays: Number(event.target.value) });
  };

  return (
    <article
      className={clsx(styles.card, isActive && styles.cardActive)}
      style={{ '--stage-accent': accentColor } as CSSProperties}
      onClick={() => onSelect(stage.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect(stage.id);
        }
      }}
      aria-pressed={isActive}
    >
      <header className={styles.header}>
        <div className={styles.stageIndex} aria-hidden>
          {index + 1}
          <span className={styles.totalIndicator}>/{total}</span>
        </div>
        <div className={styles.titleGroup}>
          <input
            className={styles.stageTitle}
            value={stage.title}
            onChange={handleInputChange('title')}
            onClick={(event) => event.stopPropagation()}
            aria-label={`Nome da etapa ${index + 1}`}
          />
          <p className={styles.persona}>{stage.personaFocus}</p>
        </div>
        <div className={styles.healthBadge}>
          <span className={styles.healthLabel}>Saúde</span>
          <span className={styles.healthValue}>{Math.round(stage.healthScore * 100)}%</span>
        </div>
      </header>
      <div className={styles.sliderGroup} onClick={(event) => event.stopPropagation()}>
        <label className={styles.sliderLabel} htmlFor={`conversion-${stage.id}`}>
          Meta de conversão
          <span className={styles.sliderValue}>{stage.targetConversion}%</span>
        </label>
        <input
          id={`conversion-${stage.id}`}
          type="range"
          min={2}
          max={80}
          step={1}
          value={stage.targetConversion}
          className={styles.sliderInput}
          onChange={handleConversionChange}
        />
        <div className={styles.sliderTrack} aria-hidden>
          <div className={styles.sliderProgress} style={{ width: `${stage.targetConversion}%` }} />
        </div>
      </div>
      <div className={styles.sliderGroup} onClick={(event) => event.stopPropagation()}>
        <label className={styles.sliderLabel} htmlFor={`velocity-${stage.id}`}>
          Tempo médio de avanço
          <span className={styles.sliderValue}>{stage.avgVelocityDays} dias</span>
        </label>
        <input
          id={`velocity-${stage.id}`}
          type="range"
          min={1}
          max={45}
          step={1}
          value={stage.avgVelocityDays}
          className={styles.sliderInput}
          onChange={handleVelocityChange}
        />
        <div className={styles.sliderTrack} aria-hidden>
          <div className={styles.sliderProgress} style={{ width: `${(stage.avgVelocityDays / 45) * 100}%` }} />
        </div>
      </div>
      <section className={styles.touchpoints}>
        <header className={styles.sectionHeader}>
          <h3>Touchpoints estratégicos</h3>
          <p>{stage.touchpoints.length} interações-chave</p>
        </header>
        <div className={styles.chipList}>
          {stage.touchpoints.map((touchpoint) => (
            <span className={styles.chip} key={touchpoint}>
              {touchpoint}
            </span>
          ))}
        </div>
      </section>
      <section className={styles.metaSection}>
        <div>
          <h3>Automação ativa</h3>
          <ul className={styles.automationList}>
            {stage.automations.map((automation) => (
              <li key={automation}>{automation}</li>
            ))}
          </ul>
        </div>
        <div className={styles.ownerCard}>
          <p className={styles.ownerLabel}>Owner</p>
          <p className={styles.ownerName}>{stage.owner}</p>
        </div>
      </section>
      <label className={styles.notesLabel}>
        Observações estratégicas
        <textarea value={stage.notes} onChange={handleInputChange('notes')} onClick={(event) => event.stopPropagation()} />
      </label>
    </article>
  );
}
