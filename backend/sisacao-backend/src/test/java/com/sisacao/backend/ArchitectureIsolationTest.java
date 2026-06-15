package com.sisacao.backend;

import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.sisacao.backend")
class ArchitectureIsolationTest {

    @ArchTest
    static final ArchRule backend_modules_are_free_of_cycles =
            slices()
                    .matching("com.sisacao.backend.(*)..")
                    .should()
                    .beFreeOfCycles()
                    .because(
                            "o relatório de evolução separa coleta, normalização, feature store, modelagem e execução; "
                                    + "os pacotes do backend devem preservar essas fronteiras sem ciclos entre módulos");
}
