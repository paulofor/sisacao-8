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
import org.springframework.stereotype.Service;

@Service
public class DataCollectionMessageService {

    private final PythonDataCollectionClient pythonClient;

    public DataCollectionMessageService(PythonDataCollectionClient pythonClient) {
        this.pythonClient = pythonClient;
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

        List<DataCollectionMessage> messages = pythonClient.fetchMessages().stream()
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
                pythonClient.fetchMessages().stream()
                        .filter(message -> isIntradayDataset(message.dataset()))
                        .max(Comparator.comparing(PythonDataCollectionClient.PythonMessage::createdAt));

        if (latestIntradayMessage.isEmpty()) {
            return IntradaySummary.empty();
        }

        return toIntradaySummary(latestIntradayMessage.get());
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
                    String error = val.toString();
                    result.put(ticker, error);
                }
            });
        } else if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    Object tickerValue = map.get("ticker");
                    Object errorValue = map.get("erro");
                    if (tickerValue != null && errorValue != null) {
                        result.put(tickerValue.toString(), errorValue.toString());
                    }
                }
            }
        }
        return result;
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
