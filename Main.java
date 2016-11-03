import javafx.util.Pair;
import net.uaprom.jmorphy2.MorphAnalyzer;
import net.uaprom.jmorphy2.ParsedWord;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

/**
 * Created by sergeybp on 27.10.16.
 */
public class Main {


    public static Integer maxID = 1;
    public static LogWriter logWriter = new LogWriter();

    static Integer ITERATIONS = 1;
    static String processedTextsPath = "processed";
    static String patterPoolPath = "patterns.xlsx";
    static String ontologyPath = "categories_animals_ru.xls";
    static String ontologyJson = "ontology1.json";
    static String patternsPoolJson = "patternsPool1.json";


    public static void main(String[] args) throws IOException {

        PatternPool patternPool = new PatternPool(patterPoolPath);
        Ontology ontology = new Ontology(ontologyPath);
        InstanceExtractor instanceExtractor = new InstanceExtractor();
        PatternExtractor patternExtractor = new PatternExtractor();
        for(int i = 0 ; i < ITERATIONS; i++){
            System.out.println("[Iteration "+i+"]");
            logWriter.write("[Iteration "+i+"]");
            ontology = instanceExtractor.learn(patternPool,ontology,processedTextsPath);
            ontology = instanceExtractor.evaluate(ontology,processedTextsPath, 1);
            Pair<HashMap<String, HashMap<String, Integer>>, PatternPool> pair = patternExtractor.learn(ontology,processedTextsPath);
            HashMap<String, HashMap<String, Integer>> promotedPatternsDict = pair.getKey();
            PatternPool promotedPatternsPool = pair.getValue();
            Pair<PatternPool, Ontology> pair1 = patternExtractor.evaluate(ontology,patternPool,promotedPatternsPool,promotedPatternsDict,processedTextsPath,0);
            patternPool = pair1.getKey();
            ontology = pair1.getValue();
            ontology.toJson(ontologyJson);
            patternPool.toJson(patternsPoolJson);

        }

    }

}
