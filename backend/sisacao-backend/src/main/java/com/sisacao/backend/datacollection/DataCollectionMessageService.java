package com.sisacao.backend.datacollection;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
}
