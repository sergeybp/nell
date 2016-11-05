import javafx.util.Pair;
import scala.Int;

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
public class InstanceExtractor {


    public Ontology learn(PatternPool patternPool, Ontology ontology, String processedTextPath) {
        //System.out.println("[InstanceExtractor] -- Learning step.");
        Main.logWriter.write("[InstanceExtractor] -- Learning step.");
        ArrayList<File> files = getFiles(processedTextPath);
        for (File file : files) {
            ProcessedText text = new ProcessedText();
            text.fromJson(file);
            for (Sentence sentence : text.sentences) {
                for (Pattern pattern : patternPool.patterns) {
                    ontology = findPatternInSentence(pattern, sentence, ontology);
                }
            }
        }
        return ontology;
    }

    Ontology evaluate(Ontology ontology, String processedTextPath, Integer treshold){
        treshold = 1;
        //System.out.println("[InstanceExtractor] -- Evaluating step.");
        Main.logWriter.write("[InstanceExtractor] -- Evaluating step.");
        for(Category instance : ontology.instances){
            HashMap<String, Double> precision = new HashMap<>();
            for(HashMap.Entry<String,Double> promotedInstance : instance.promotedInstances.entrySet()){
                Double numOfCoOccurence = promotedInstance.getValue();
                Integer numInText = findNumberOfInstanceInText(promotedInstance, processedTextPath);
                precision.put(promotedInstance.getKey(), numOfCoOccurence/(Double.valueOf(""+numInText)));
            }
            Integer i = precision.size() -treshold  - 1;
            while ( i > 0){
                Double min = 10000000d;
                String key = "";
                for(HashMap.Entry<String,Double> item : precision.entrySet()){
                    if(item.getValue() < min){
                        key = item.getKey();
                        min = item.getValue();
                    }
                }
                precision.remove(key);
                i--;
            }
            instance.promotedInstances = new HashMap<>();
            for(HashMap.Entry<String,Double> promotedInstance : precision.entrySet()){

                if(instance.addPromotedInstances(promotedInstance.getKey())){
                    //System.out.println("Adding new instance" +promotedInstance.getKey()+ "to Category" +instance.ctaegoryName+ "with precision value " + promotedInstance.getValue());
                    Main.logWriter.write("Adding new instance [" +promotedInstance.getKey()+ "] to Category [" +instance.ctaegoryName+ "] with precision value [" + promotedInstance.getValue()+"]");

                }
            }

        }

        return ontology;
    }

    Integer findNumberOfInstanceInText(HashMap.Entry<String,Double> instance, String processedTextPath){
        int count = 0;
        ArrayList<File> files = getFiles(processedTextPath);
        for (File file : files) {
            ProcessedText text = new ProcessedText();
            text.fromJson(file);
            for (Sentence sentence : text.sentences) {
                for(SimpleWord word : sentence.words){
                    if (word.isPunctuation){
                        continue;
                    }
                    if(word.lexem.equals(instance.getKey())){
                        count++;
                    }
                }
            }
        }
        return count;
    }

    Ontology findPatternInSentence(Pattern pattern, Sentence sentence, Ontology ontology) {

        ArrayList<String> patternString = splitSentence(pattern.pattern);
        for (int i = 0; i < sentence.words.size() - patternString.size() + 1; i++) {
            ArrayList<SimpleWord> sentencePart = new ArrayList<>();
            for (int j = i; j < patternString.size(); j++) {
                sentencePart.add(sentence.words.get(j));
            }
            Pair<Integer, Integer> tmp = checkIfPatternExists(sentencePart, pattern);
            Integer arg1pos = tmp.getKey();
            Integer arg2pos = tmp.getValue();
            if (arg1pos != null && arg2pos != null) {
                arg1pos += i;
                arg2pos += i;
                SimpleWord arg1 = sentence.words.get(arg1pos);
                SimpleWord arg2 = sentence.words.get(arg2pos);
                for (Category category : ontology.instances) {
                    if (arg1.lexem.equals(category.ctaegoryName)) {
                        if (checkWordForPattern(arg1, pattern.arg1)) {
                            if (checkWordForPattern(arg2, pattern.arg2)) {

                                //System.out.println("Found new promoted instance " + arg2.lexem + " in sentence " + sentence.stringg + " with pattern " + pattern.pattern);
                                Main.logWriter.write("Found new promoted instance [" + arg2.lexem + "] in sentence [" + sentence.stringg + "] with pattern [" + pattern.pattern+"]");
                                if (category.promotedInstances.containsKey(arg2.lexem)) {
                                    Double a = category.promotedInstances.get(arg2.lexem);
                                    category.promotedInstances.put(arg2.lexem, a + 1d);
                                } else {
                                    category.promotedInstances.put(arg2.lexem, 1d);
                                }
                            }
                        }
                    }
                }
            }
        }
        return ontology;
    }


    Boolean checkWordForPattern(SimpleWord word, PatternTemplateWord patterWord) {
        if (word.casee.toLowerCase().equals(patterWord.casee.toLowerCase()) && word.pos.toLowerCase().equals(patterWord.pos.toLowerCase())) {
            if (word.number.toLowerCase().equals(patterWord.number.toLowerCase()) || patterWord.number.equals("all")) {
                return true;
            }
        }
        return false;
    }

    Pair<Integer, Integer> checkIfPatternExists(ArrayList<SimpleWord> sentencePart, Pattern pattern) {
        Boolean flag = false;
        Integer arg1pos = null;
        Integer arg2pos = null;
        ArrayList<String> patternWords = splitSentence(pattern.pattern);
        for (int i = 0; i < sentencePart.size(); i++) {
            if (patternWords.get(i).equals("arg1")) {
                arg1pos = i;
                continue;
            } else if (patternWords.get(i).equals("arg2")) {
                arg2pos = i;
                continue;
            } else if (!patternWords.get(i).equals(sentencePart.get(i).original)) {
                return new Pair<>(null, null);
            }

        }

        return new Pair<>(arg1pos, arg2pos);

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
                if(tmp.equals("") && SimpleWord.isPunctuation(String.valueOf(stringg.charAt(i)))){
                    res.add(String.valueOf(stringg.charAt(i)));
                }
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

}
