import javafx.util.Pair;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Stream;

/**
 * Created by sergeybp on 30.10.16.
 */
public class PatternExtractor {

    public Pair<HashMap<String, HashMap<String, Integer>>, PatternPool> learn(Ontology ontology, String processedTextPath) {
        System.out.println("[Pattern Extractor] Learning step.");
        Main.logWriter.write("[Pattern Extractor] Learning step.");
        HashMap<String, HashMap<String, Integer>> promotedPatternsDict = new HashMap<>();
        PatternPool promotedPatternsPool = new PatternPool();
        ArrayList<File> files = getFiles(processedTextPath);
        for (File file : files) {
            ProcessedText text = new ProcessedText();
            text.fromJson(file);
            for (Sentence sentence : text.sentences) {
                for (Category instance : ontology.instances) {
                    Pair<Integer, Integer> poss = findPatternInSentence(sentence, instance);
                    Integer pos1 = poss.getKey();
                    Integer pos2 = poss.getValue();
                    if (pos1 == null || pos2 == null) {
                        continue;
                    }
                    if (Math.abs(pos1 - pos2) >= 5) {
                        continue;
                    }
                    String patternString = "";
                    if (pos1 < pos2) {
                        patternString = "arg1 ";
                        for (int i = pos1 + 1; i < pos2; i++) {
                            patternString += sentence.words.get(i).original;
                            patternString += " ";
                        }
                        patternString += "arg2";
                    } else {
                        patternString = "arg2 ";
                        for(int i = pos2 + 1; i < pos1; i++){
                            patternString += sentence.words.get(i).original;
                            patternString += " ";
                        }
                        patternString += "arg1";
                    }
                    PatternTemplateWord patternWord1 = new PatternTemplateWord(sentence.words.get(pos1).casee, sentence.words.get(pos1).number,sentence.words.get(pos1).pos);
                    PatternTemplateWord patternWord2 = new PatternTemplateWord(sentence.words.get(pos2).casee, sentence.words.get(pos2).number,sentence.words.get(pos2).pos);
                    if(!promotedPatternsDict.keySet().contains(patternString)){
                        promotedPatternsDict.put(patternString, new HashMap<>());
                    }
                    if(promotedPatternsDict.get(patternString).containsKey(instance.ctaegoryName)){
                        Integer a = promotedPatternsDict.get(patternString).get(instance.ctaegoryName);
                        a++;
                        promotedPatternsDict.get(patternString).put(instance.ctaegoryName,a);
                    } else {
                        promotedPatternsDict.get(patternString).put(instance.ctaegoryName,1);
                    }
                    Pattern pattern = new Pattern(Main.maxID+1,patternString,patternWord1,patternWord2);
                    Main.maxID = Main.maxID + 1;
                    promotedPatternsPool.addPattern(pattern);
                    //TODO log
                    //System.out.println("Found new promoted pattern "+patternString+" in sentence "+sentence.stringg+".");
                    Main.logWriter.write("Found new promoted pattern ["+patternString+"] in sentence ["+sentence.stringg+"]");
                }
            }
        }
        return new Pair<>(promotedPatternsDict,promotedPatternsPool);
    }

    public Pair<PatternPool, Ontology> evaluate(Ontology ontology, PatternPool patternPool, PatternPool promotedPatternsPool, HashMap<String, HashMap<String, Integer>> promotedPatternsDict, String processedTextPath, Integer treshold){
        treshold = 0;
        //System.out.println("[Pattern Extractor] Evaluating step.");
        Main.logWriter.write("[Pattern Extractor] Evaluating step.");
        HashMap<String, Integer> patternsInText = patternsInTextDict(promotedPatternsPool, processedTextPath);
        for(Category instance : ontology.instances){
            HashMap<String, Double> precision = new HashMap<>();
            for(Pattern pattern : promotedPatternsPool.patterns){
                Integer numOfCoOccurence = null;
                if(promotedPatternsDict.containsKey(pattern.pattern)){
                    if(promotedPatternsDict.get(pattern.pattern).containsKey(instance.ctaegoryName)){
                        numOfCoOccurence = promotedPatternsDict.get(pattern.pattern).get(instance.ctaegoryName);
                    } else {
                        continue;
                    }
                } else {
                    continue;
                }
                Integer numInText = null;
                if(patternsInText.containsKey(pattern.pattern)){
                    numInText = patternsInText.get(pattern.pattern);
                } else {
                    continue;
                }
                if(numOfCoOccurence != null && numInText != null){
                    precision.put(pattern.pattern, Double.valueOf(numOfCoOccurence) / Double.valueOf(numInText));
                }
            }
            ValueComparator bvc = new ValueComparator(precision);
            TreeMap<String, Double> sPrecision = new TreeMap<String, Double>(bvc);
            sPrecision.putAll(precision);

            Integer i = sPrecision.size() - treshold - 1;
            for(Map.Entry<String,Double> item: sPrecision.entrySet()){
                if(i <= 0){
                    break;
                }
                sPrecision.remove(item.getKey());
                i -= 1;
            }
            for(Pattern pattern : promotedPatternsPool.patterns){
                Double precisio = 0d;
                try {
                    precisio = sPrecision.get(pattern.pattern);
                }
                 catch (Exception e){
                    continue;
                }
                if(instance.addPromotedPattern(pattern,promotedPatternsPool,patternPool)){
                    patternPool.addPattern(pattern);
                    //TODO log
                    //System.out.println("Add pattern "+pattern.pattern+" for category "+instance.ctaegoryName+" with precision score " + precisio);
                    Main.logWriter.write("Add pattern ["+pattern.pattern+"] for category ["+instance.ctaegoryName+"] with precision score [" + precisio+"]");
                }
            }

        }
        return new Pair<>(patternPool,ontology);
    }

    HashMap<String, Integer> patternsInTextDict(PatternPool promotedPatternsPool, String processedTextPath){
        HashMap<String,Integer> patternsInTextDict = new HashMap<>();
        ArrayList<File> files = getFiles(processedTextPath);
        for (File file : files) {
            ProcessedText text = new ProcessedText();
            text.fromJson(file);
            for (Sentence sentence : text.sentences) {
                ArrayList<String> sentenceTokenize = new ArrayList<>();
                for(SimpleWord word : sentence.words){
                    sentenceTokenize.add(word.original);
                }
                for(Pattern pattern : promotedPatternsPool.patterns){
                    ArrayList<String> patternTokenize = splitSentence(pattern.pattern);
                    if(!patternTokenize.contains("arg2")){
                        continue;
                    } else {
                        patternTokenize.remove("arg2");
                    }
                    if(!patternTokenize.contains("arg1")){
                        continue;
                    } else {
                        patternTokenize.remove("arg1");
                    }
                    if(subFinder(sentenceTokenize,patternTokenize)){
                        if (patternsInTextDict.containsKey(pattern.pattern)){
                            Integer a = patternsInTextDict.get(pattern.pattern);
                            a++;
                            patternsInTextDict.put(pattern.pattern,a);
                        } else {
                            patternsInTextDict.put(pattern.pattern,1);
                        }
                    }
                }

            }
        }
        return patternsInTextDict;
    }

    Boolean subFinder(ArrayList<String> sentenceTokenize, ArrayList<String> patternTokenize){
        int check = 0;
        for(String s : patternTokenize){
            if(!sentenceTokenize.contains(s)){
                check++;
            }
        }
        if(check == patternTokenize.size()){
            return true;
        }
        return false;
    }

    Pair<Integer, Integer> findPatternInSentence(Sentence sentence, Category instance) {
        Integer pos1 = null;
        Integer pos2 = null;
        String arg1 = instance.ctaegoryName;
        for (String arg2 : instance.instances) {
            Pair<Integer, Integer> res = sentence.findWordsInSentence(arg1, arg2);
            pos1 = res.getKey();
            pos2 = res.getValue();
            if (res.getKey() != null && res.getValue() != null) {
                return res;
            }
        }
        return new Pair<>(pos1, pos2);
    }

    ArrayList<File> getFiles(String path) {
        ArrayList<File> res = new ArrayList<>();
        try (Stream<Path> paths = Files.walk(Paths.get(path))) {
            paths.forEach(filePath -> {
                if (Files.isRegularFile(filePath)) {
                    res.add(new File(String.valueOf(filePath)));
                }
            });
        } catch (IOException e) {
            e.printStackTrace();
        }
        return res;
    }

    public ArrayList<String> splitSentence(String stringg) {
        String tmp = "";
        ArrayList<String> res = new ArrayList<>();
        for (int i = 0; i < stringg.length(); i++) {
            if (SimpleWord.isPunctuation(String.valueOf(stringg.charAt(i))) || stringg.charAt(i) == ' ') {
                if (!tmp.equals("")) {
                    res.add(tmp);
                    if(stringg.charAt(i) != ' '){
                        res.add(String.valueOf(stringg.charAt(i)));
                    }
                    tmp = "";
                }
            } else {
                tmp += stringg.charAt(i);
                if(i == stringg.length() -1){
                    res.add(tmp);
                }
            }
        }
        return res;
    }

    class ValueComparator implements Comparator<String> {
        Map<String, Double> base;

        public ValueComparator(Map<String, Double> base) {
            this.base = base;
        }

        // Note: this comparator imposes orderings that are inconsistent with
        // equals.
        public int compare(String a, String b) {
            if (base.get(a) >= base.get(b)) {
                return -1;
            } else {
                return 1;
            } // returning 0 would merge keys
        }
    }

}