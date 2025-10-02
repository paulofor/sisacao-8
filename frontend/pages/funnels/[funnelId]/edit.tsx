import Head from 'next/head';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import FunnelStageCard, { FunnelStage } from '@/components/FunnelStageCard';
import DashboardShell from '@/components/Layout/DashboardShell';
import MetricSummaryCard from '@/components/MetricSummaryCard';
import styles from '@/styles/FunnelEditPage.module.css';

type FunnelDetails = {
  name: string;
  mission: string;
  goal: string;
  ownerTeam: string;
  reviewCadence: string;
  persona: string;
  stages: FunnelStage[];
};

const stagePalette = ['#38bdf8', '#a855f7', '#f97316', '#facc15', '#22d3ee'];

const initialFunnel: FunnelDetails = {
  name: 'Funil de aquisição Enterprise',
  mission: 'Reforçar autoridade, qualificar contas e acelerar fechamento de deals enterprise.',
  goal: 'Pipeline mensal em R$ 1.2M com ciclo médio abaixo de 35 dias.',
  ownerTeam: 'Revenue Ops + Marketing Performance',
  reviewCadence: 'Revisão quinzenal com sales leaders',
  persona: 'C-Levels e Heads de Tecnologia em empresas de médio e grande porte',
  stages: [
    {
      id: 'stage-awareness',
      title: 'Descoberta orientada por insights',
      personaFocus: 'Top accounts do segmento SaaS B2B',
      targetConversion: 22,
      avgVelocityDays: 6,
      owner: 'Squad de Inbound',
      automations: ['Newsletter interativa com benchmark setorial', 'Sequência de social selling'],
      notes: 'Priorizar campanhas com dados proprietários e incluir CTA para diagnóstico guiado.',
      touchpoints: ['Relatório interativo', 'Anúncios LinkedIn com prova social', 'Webinar com cliente referência'],
      healthScore: 0.82
    },
    {
      id: 'stage-consideration',
      title: 'Diagnóstico consultivo e alinhamento',
      personaFocus: 'Buying committee técnico + negócio',
      targetConversion: 35,
      avgVelocityDays: 10,
      owner: 'Equipe de pré-venda',
      automations: ['Playbook de discovery com IA', 'Sequência multi-touch de nurturing'],
      notes: 'Atualizar roteiro de perguntas e enviar sumário executivo personalizado em até 24 horas.',
      touchpoints: ['Discovery call', 'Envio de business case', 'Workshop remoto de ROI'],
      healthScore: 0.74
    },
    {
      id: 'stage-decision',
      title: 'Co-criação da proposta e champion enablement',
      personaFocus: 'CFO + CTO',
      targetConversion: 48,
      avgVelocityDays: 14,
      owner: 'Account Executives',
      automations: ['Template dinâmico de proposta', 'Fluxo de onboarding antecipado'],
      notes: 'Garantir aprovação jurídica em paralelo e preparar plano de impacto para os primeiros 90 dias.',
      touchpoints: ['Demo executiva', 'Sessão técnica com engenharia', 'Proposta interativa'],
      healthScore: 0.69
    }
  ]
};

export default function FunnelEditPage() {
  const [funnel, setFunnel] = useState<FunnelDetails>(initialFunnel);
  const [selectedStageId, setSelectedStageId] = useState<string>(initialFunnel.stages[0]?.id ?? '');

  const selectedStage = useMemo(
    () => funnel.stages.find((stage) => stage.id === selectedStageId) ?? funnel.stages[0],
    [funnel.stages, selectedStageId]
  );

  const funnelVelocity = useMemo(() => {
    if (funnel.stages.length === 0) {
      return 0;
    }

    const totalDays = funnel.stages.reduce((accumulator, stage) => accumulator + stage.avgVelocityDays, 0);
    return Math.round(totalDays);
  }, [funnel.stages]);

  const aggregateConversion = useMemo(() => {
    if (funnel.stages.length === 0) {
      return 0;
    }

    const combined = funnel.stages.reduce((accumulator, stage) => accumulator * (stage.targetConversion / 100), 1);
    return Math.round(combined * 1000) / 10;
  }, [funnel.stages]);

  const updateStage = (stageId: string, patch: Partial<FunnelStage>) => {
    setFunnel((current) => ({
      ...current,
      stages: current.stages.map((stage) => (stage.id === stageId ? { ...stage, ...patch } : stage))
    }));
  };

  const stageFocusIndex = funnel.stages.findIndex((stage) => stage.id === selectedStage?.id);

  return (
    <DashboardShell
      breadcrumbs={[
        { label: 'Growth Studio', href: '/' },
        { label: 'Funis' },
        { label: funnel.name }
      ]}
      actions={
        <div className={styles.headerActions}>
          <Link className={styles.secondaryAction} href="#colaboradores">
            Compartilhar
          </Link>
          <button className={styles.secondaryAction} type="button">
            Pré-visualizar
          </button>
          <button className={styles.primaryAction} type="button">
            Publicar alterações
          </button>
        </div>
      }
    >
      <Head>
        <title>{`Editar • ${funnel.name}`}</title>
      </Head>
      <div className={styles.pageWrapper}>
        <header className={styles.pageHeader}>
          <div className={styles.badges}>
            <span className={styles.badge}>Funil estratégico</span>
            <span className={styles.badge}>Última atualização há 2 dias</span>
          </div>
          <div className={styles.titleGroup}>
            <h1>{funnel.name}</h1>
            <p>{funnel.mission}</p>
          </div>
          <dl className={styles.metaGrid}>
            <div>
              <dt>Meta central</dt>
              <dd>{funnel.goal}</dd>
            </div>
            <div>
              <dt>Owner</dt>
              <dd>{funnel.ownerTeam}</dd>
            </div>
            <div>
              <dt>Persona</dt>
              <dd>{funnel.persona}</dd>
            </div>
            <div>
              <dt>Ritual de revisão</dt>
              <dd>{funnel.reviewCadence}</dd>
            </div>
          </dl>
        </header>
        <div className={styles.contentGrid}>
          <section className={styles.primaryColumn}>
            <div className={styles.stageListHeader}>
              <div>
                <h2>Arquitetura das etapas</h2>
                <p>Selecione uma etapa para ajustar conversões, cadências e playbooks.</p>
              </div>
              <button className={styles.outlineButton} type="button">
                Adicionar etapa
              </button>
            </div>
            <div className={styles.stageStack}>
              {funnel.stages.map((stage, index) => (
                <FunnelStageCard
                  key={stage.id}
                  stage={stage}
                  index={index}
                  total={funnel.stages.length}
                  accentColor={stagePalette[index % stagePalette.length]}
                  isActive={stage.id === selectedStage?.id}
                  onSelect={setSelectedStageId}
                  onStageChange={updateStage}
                />
              ))}
            </div>
          </section>
          <aside className={styles.secondaryColumn}>
            <div className={styles.summaryCard}>
              <h2>Saúde geral do funil</h2>
              <div className={styles.summaryMetrics}>
                <MetricSummaryCard
                  label="Conversão acumulada"
                  value={`${aggregateConversion.toFixed(1)}%`}
                  trendLabel="vs. mês anterior"
                  trendValue="+4.6%"
                  trendDirection="up"
                />
                <MetricSummaryCard
                  label="Tempo médio"
                  value={`${funnelVelocity} dias`}
                  trendLabel="última sprint"
                  trendValue="-3 dias"
                  trendDirection="up"
                />
              </div>
              <div className={styles.timeline}>
                {funnel.stages.map((stage, index) => (
                  <div className={styles.timelineStage} key={stage.id} data-active={stage.id === selectedStage?.id}>
                    <div className={styles.timelineBullet} style={{ background: stagePalette[index % stagePalette.length] }} />
                    <div className={styles.timelineContent}>
                      <p>{stage.title}</p>
                      <span>{stage.targetConversion}% · {stage.avgVelocityDays} dias</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className={styles.focusCard}>
              <h2>Próxima ação prioritária</h2>
              <p>
                {selectedStage
                  ? `Foque em "${selectedStage.title}". Ajuste o roteiro do time ${selectedStage.owner} e valide novo material
                para ${selectedStage.touchpoints[0]}.`
                  : 'Selecione uma etapa para destravar recomendações personalizadas.'}
              </p>
              <button className={styles.primaryAction} type="button">
                Criar plano de ação
              </button>
            </div>
            <div className={styles.guidelinesCard}>
              <h2>Guidelines de UX & experimentação</h2>
              <ul>
                <li>Evite gargalos mantendo feedback real-time com times de vendas.</li>
                <li>Defina hipóteses claras e priorize testes com maior impacto esperado.</li>
                <li>Sincronize dados de engajamento entre CRM, produto e marketing.</li>
              </ul>
            </div>
            <div className={styles.progressCard}>
              <h2>Ritual de acompanhamento</h2>
              <ol>
                <li>
                  <strong>Daily de 15min</strong>
                  <span>Monitoramento das métricas críticas por squad.</span>
                </li>
                <li>
                  <strong>Sprint review quinzenal</strong>
                  <span>Alinhar com stakeholders e atualizar playbooks.</span>
                </li>
                <li>
                  <strong>Executive sync mensal</strong>
                  <span>Compartilhar resultados e decisões estratégicas.</span>
                </li>
              </ol>
            </div>
          </aside>
        </div>
        <footer className={styles.footerBar}>
          <div>
            <p className={styles.footerTitle}>Etapa em foco</p>
            <p className={styles.footerDescription}>
              {selectedStage
                ? `${stageFocusIndex + 1}/${funnel.stages.length} • ${selectedStage.title}`
                : 'Selecione uma etapa para editar'}
            </p>
          </div>
          <div className={styles.footerActions}>
            <button className={styles.secondaryAction} type="button">
              Desfazer
            </button>
            <button className={styles.secondaryAction} type="button">
              Duplicar etapa
            </button>
            <button className={styles.primaryAction} type="button">
              Salvar rascunho
            </button>
          </div>
        </footer>
      </div>
    </DashboardShell>
  );
}
