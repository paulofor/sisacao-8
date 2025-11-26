package com.sisacao.backend.datacollection;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class DataCollectionMessageService {

    private static final Logger LOGGER = LoggerFactory.getLogger(DataCollectionMessageService.class);

    private final PythonDataCollectionClient pythonClient;
    private final Optional<BigQueryCollectionMessageClient> bigQueryClient;
    private final Optional<BigQueryIntradayMetricsClient> intradayMetricsClient;

    public DataCollectionMessageService(
            PythonDataCollectionClient pythonClient,
            Optional<BigQueryCollectionMessageClient> bigQueryClient,
            Optional<BigQueryIntradayMetricsClient> intradayMetricsClient) {
        this.pythonClient = pythonClient;
        this.bigQueryClient = bigQueryClient;
        this.intradayMetricsClient = intradayMetricsClient;
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

        List<DataCollectionMessage> messages = loadMessages().stream()
                .map(this::toDataCollectionMessage)
                .sorted(Comparator.comparing(DataCollectionMessage::createdAt).reversed())
                .collect(Collectors.toList());

        Stream<DataCollectionMessage> stream = messages.stream();

        if (severity.isPresent()) {
            DataCollectionMessageSeverity targetSeverity = severity.get();
            stream = stream.filter(message -> message.severity() == targetSeverity);
        }

        if (collector.isPresent()) {
            String normalizedCollector = collector.get().toLowerCase();
            stream = stream.filter(message -> message.collector().equalsIgnoreCase(normalizedCollector));
        }

        List<DataCollectionMessage> filtered = stream.collect(Collectors.toList());

        return limit.map(integer -> filtered.stream().limit(integer).collect(Collectors.toList())).orElse(filtered);
    }

    public IntradaySummary buildIntradaySummary() {
        Optional<PythonDataCollectionClient.PythonMessage> latestIntradayMessage =
                loadMessages().stream()
                        .filter(message -> isIntradayDataset(message.dataset()))
                        .max(Comparator.comparing(PythonDataCollectionClient.PythonMessage::createdAt));

        if (latestIntradayMessage.isEmpty()) {
            return IntradaySummary.empty();
        }

        return toIntradaySummary(latestIntradayMessage.get());
    }

    public List<IntradayDailyCount> fetchIntradayDailyCounts() {
        return intradayMetricsClient.map(BigQueryIntradayMetricsClient::fetchDailyCounts).orElseGet(List::of);
    }

    private List<PythonDataCollectionClient.PythonMessage> loadMessages() {
        if (bigQueryClient.isPresent()) {
            try {
                List<PythonDataCollectionClient.PythonMessage> messages = bigQueryClient.get().fetchMessages();
                if (!messages.isEmpty()) {
                    return messages;
                }
                LOGGER.debug(
                        "BigQuery returned no collection messages. Falling back to python script source.");
            } catch (RuntimeException ex) {
                LOGGER.warn(
                        "Failed to fetch collection messages from BigQuery. Falling back to python script.",
                        ex);
            }
        }
        return pythonClient.fetchMessages();
    }

    private DataCollectionMessage toDataCollectionMessage(PythonDataCollectionClient.PythonMessage raw) {
        DataCollectionMessageSeverity severity =
                Optional.ofNullable(raw.severity())
                        .map(DataCollectionMessageSeverity::fromString)
                        .orElse(DataCollectionMessageSeverity.UNKNOWN);

        Map<String, Object> metadata =
                Optional.ofNullable(raw.metadata()).orElseGet(Map::of);
        return new DataCollectionMessage(
                raw.id(),
                raw.collector(),
                severity,
                raw.summary(),
                raw.dataset(),
                raw.createdAt(),
                metadata);
    }

    private boolean isIntradayDataset(String dataset) {
        if (dataset == null) {
            return false;
        }
        return dataset.toLowerCase().contains("cotacao_intraday.cotacao_bovespa");
    }

    private IntradaySummary toIntradaySummary(PythonDataCollectionClient.PythonMessage message) {
        Map<String, Object> metadata = Optional.ofNullable(message.metadata()).orElseGet(Map::of);

        List<String> requestedTickers = extractTickerList(metadata.get("tickersSolicitados"));
        Map<String, Double> pricesByTicker = extractPrices(metadata.get("cotacoes"));
        Map<String, String> failures = extractFailures(metadata.get("falhas"));

        Set<String> orderedTickers = new LinkedHashSet<>();
        if (!requestedTickers.isEmpty()) {
            orderedTickers.addAll(requestedTickers);
        }
        orderedTickers.addAll(pricesByTicker.keySet());
        orderedTickers.addAll(failures.keySet());

        List<IntradayTickerSummary> tickers = new ArrayList<>();
        for (String ticker : orderedTickers) {
            Double price = pricesByTicker.get(ticker);
            String error = failures.get(ticker);
            boolean success = price != null && (error == null || error.isBlank());
            tickers.add(new IntradayTickerSummary(ticker, price, success, error));
        }

        int total = tickers.size();
        int successCount = (int) tickers.stream().filter(IntradayTickerSummary::success).count();
        int failureCount =
                (int)
                        tickers.stream()
                                .filter(ticker -> !ticker.success() && ticker.error() != null && !ticker.error().isBlank())
                                .count();

        return new IntradaySummary(message.createdAt(), total, successCount, failureCount, tickers);
    }

    private List<String> extractTickerList(Object value) {
        if (value instanceof List<?> list) {
            return list.stream()
                    .filter(Objects::nonNull)
                    .map(Object::toString)
                    .map(String::trim)
                    .filter(str -> !str.isEmpty())
                    .collect(Collectors.toList());
        }
        if (value instanceof String str) {
            String[] parts = str.split(",");
            return Stream.of(parts)
                    .map(String::trim)
                    .filter(part -> !part.isEmpty())
                    .collect(Collectors.toList());
        }
        return List.of();
    }

    private Map<String, Double> extractPrices(Object value) {
        Map<String, Double> result = new LinkedHashMap<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    Object tickerValue = map.get("ticker");
                    if (tickerValue == null) {
                        continue;
                    }
                    String ticker = tickerValue.toString();
                    Double price = extractDouble(map.get("valor"));
                    if (price == null) {
                        price = extractDouble(map.get("price"));
                    }
                    if (price != null) {
                        result.put(ticker, price);
                    }
                }
            }
        }
        return result;
    }

    private Map<String, String> extractFailures(Object value) {
        Map<String, String> result = new LinkedHashMap<>();
        if (value instanceof Map<?, ?> map) {
            map.forEach((key, val) -> {
                if (key != null && val != null) {
                    String ticker = key.toString();
                    String error = formatFailureDetail(val);
                    result.put(ticker, error);
                }
            });
        } else if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    Object tickerValue = map.get("ticker");
                    Object errorValue = map.get("erro");
                    if (tickerValue != null && errorValue != null) {
                        result.put(tickerValue.toString(), formatFailureDetail(errorValue));
                    }
                }
            }
        }
        return result;
    }

    private String formatFailureDetail(Object value) {
        if (value instanceof Map<?, ?> detailMap) {
            Object message = detailMap.get("message");
            Object type = detailMap.get("type");
            Object status = detailMap.get("status");
            Object cause = detailMap.get("cause");
            Object url = detailMap.get("url");
            Object excerpt = detailMap.get("responseExcerpt");

            StringBuilder builder = new StringBuilder();
            if (type instanceof String typeStr && !typeStr.isBlank()) {
                builder.append(typeStr);
            }
            if (message != null) {
                String messageStr = message.toString();
                if (!messageStr.isBlank()) {
                    if (builder.length() > 0) {
                        builder.append(": ");
                    }
                    builder.append(messageStr);
                }
            }
            if (status instanceof String statusStr && !statusStr.isBlank()) {
                builder.append(" (status ").append(statusStr).append(")");
            } else if (status instanceof Number number) {
                builder.append(" (status ").append(number).append(")");
            }
            if (cause instanceof String causeStr && !causeStr.isBlank()) {
                builder.append(" — causa: ").append(causeStr);
            }
            if (url instanceof String urlStr && !urlStr.isBlank()) {
                builder.append(" — url: ").append(urlStr);
            }
            if (excerpt instanceof String excerptStr && !excerptStr.isBlank()) {
                builder.append(" — resposta: ").append(excerptStr);
            }
            if (builder.length() > 0) {
                return builder.toString();
            }
        }
        return value != null ? value.toString() : "";
    }

    private Double extractDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String str) {
            try {
                return Double.parseDouble(str);
            } catch (NumberFormatException ex) {
                return null;
            }
        }
        return null;
    }
}
