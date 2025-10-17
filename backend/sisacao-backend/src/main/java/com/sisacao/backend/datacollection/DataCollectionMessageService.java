package com.sisacao.backend.datacollection;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.springframework.stereotype.Service;

@Service
public class DataCollectionMessageService {

    private final List<DataCollectionMessage> sampleMessages;

    public DataCollectionMessageService() {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        this.sampleMessages = List.of(
                new DataCollectionMessage(
                        "evt-001",
                        "ingestao-b3",
                        DataCollectionMessageSeverity.SUCCESS,
                        "Carga diária concluída com sucesso.",
                        "bronze.cotacoes_b3",
                        now.minusMinutes(3),
                        Map.of("linhasProcessadas", 1250, "duracaoSegundos", 42)),
                new DataCollectionMessage(
                        "evt-002",
                        "ingestao-crypto",
                        DataCollectionMessageSeverity.WARNING,
                        "Oscilação detectada durante a coleta de preços.",
                        "bronze.cotacoes_crypto",
                        now.minusMinutes(12),
                        Map.of("exchange", "Binance", "paresAfetados", 3)),
                new DataCollectionMessage(
                        "evt-003",
                        "ingestao-b3",
                        DataCollectionMessageSeverity.ERROR,
                        "Falha ao escrever no BigQuery.",
                        "silver.cotacoes_ajustadas",
                        now.minusMinutes(27),
                        Map.of("stacktraceId", "a1b2c3", "retriesExecutados", 2)),
                new DataCollectionMessage(
                        "evt-004",
                        "ingestao-news",
                        DataCollectionMessageSeverity.INFO,
                        "Coleta agendada iniciada.",
                        "raw.noticias",
                        now.minusMinutes(40),
                        Map.of("fonte", "B3", "artigosCarregados", 15)),
                new DataCollectionMessage(
                        "evt-005",
                        "ingestao-crypto",
                        DataCollectionMessageSeverity.CRITICAL,
                        "Falha geral na ingestão de ordens.",
                        "gold.ordens_criticas",
                        now.minusMinutes(55),
                        Map.of("acaoRecomendada", "Acionar suporte")));
    }

    public List<DataCollectionMessage> findMessages(
            String severityFilter, String collectorFilter, Integer limitFilter) {
        Optional<DataCollectionMessageSeverity> severity =
                Optional.ofNullable(severityFilter)
                        .map(DataCollectionMessageSeverity::fromString)
                        .filter(s -> s != DataCollectionMessageSeverity.UNKNOWN);

        Optional<String> collector =
                Optional.ofNullable(collectorFilter).map(String::trim).filter(value -> !value.isEmpty());

        Optional<Integer> limit =
                Optional.ofNullable(limitFilter).filter(value -> value != null && value > 0);

        Stream<DataCollectionMessage> stream = sampleMessages.stream();

        if (severity.isPresent()) {
            DataCollectionMessageSeverity targetSeverity = severity.get();
            stream = stream.filter(message -> message.severity() == targetSeverity);
        }

        if (collector.isPresent()) {
            String normalizedCollector = collector.get().toLowerCase();
            stream = stream.filter(message -> message.collector().equalsIgnoreCase(normalizedCollector));
        }

        List<DataCollectionMessage> filtered =
                stream.sorted(Comparator.comparing(DataCollectionMessage::createdAt).reversed())
                        .collect(Collectors.toCollection(ArrayList::new));

        return limit.map(integer -> filtered.stream().limit(integer).collect(Collectors.toList())).orElse(filtered);
    }
}
