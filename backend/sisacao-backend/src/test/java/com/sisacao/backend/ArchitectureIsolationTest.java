package com.sisacao.backend;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.sisacao.backend")
class ArchitectureIsolationTest {

    private static final String QUALITATIVE_MODULE = "..qualitative..";

    @ArchTest
    static final ArchRule qualitative_module_is_not_used_by_existing_modules =
            noClasses()
                    .that()
                    .resideOutsideOfPackage(QUALITATIVE_MODULE)
                    .should()
                    .dependOnClassesThat()
                    .resideInAPackage(QUALITATIVE_MODULE)
                    .because(
                            "o módulo de sistemas qualitativos deve nascer isolado e só ser integrado por contratos explícitos");

    @ArchTest
    static final ArchRule qualitative_module_does_not_depend_on_existing_modules =
            noClasses()
                    .that()
                    .resideInAPackage(QUALITATIVE_MODULE)
                    .should()
                    .dependOnClassesThat()
                    .resideOutsideOfPackages(QUALITATIVE_MODULE, "java..")
                    .because(
                            "o módulo qualitativo deve evoluir primeiro como fronteira isolada, sem acoplamento aos módulos atuais");
}
