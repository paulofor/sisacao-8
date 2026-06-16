package com.sisacao.backend.ops;

import java.util.List;

public record QuantPaperTradingPayload(
        QuantPaperTradingDashboard dashboard,
        List<QuantPaperTradingOrder> openOrders,
        List<QuantPaperTradingOrder> closedOrders,
        List<QuantOperationalDiaryEvent> diary) {}
