import javafx.util.Pair;
import net.uaprom.jmorphy2.MorphAnalyzer;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;


import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;

/**
 * Created by sergeybp on 27.10.16.
 */
public class Sentence {

    public ArrayList<SimpleWord> words;

    String stringg;

    Sentence(String sentence, MorphAnalyzer analyzer){
        if(sentence == null){
            return;
        }
        stringg = sentence;
        ArrayList<String> splttedWords = splitSentence();
        for(String tmp : splttedWords){
            words.add(new SimpleWord(tmp, analyzer));
        }
    }

    public ArrayList<String> splitSentence() {
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

    public Pair<Integer, Integer> findWordsInSentence(String word1, String word2){
        Integer pos1 = null;
        Integer pos2 = null;
        for(int i = 0 ; i < words.size(); i ++){
            if(word1.equals(words.get(i).lexem)){
                pos1 = i;
            }
            if(word2.equals(words.get(i).lexem)){
                pos2 = i;
            }
        }
        return new Pair<>(pos1,pos2);

    }


    public void fromJson(JSONObject sentenceJson){
        words = new ArrayList<>();
        stringg = "";
        for(int i = 0 ; i < sentenceJson.size()-1; i++){
            SimpleWord tmpWord = new SimpleWord(null,null);
            tmpWord.fromJson((JSONObject) sentenceJson.get(""+i));
            words.add(tmpWord);
        }
        stringg = (String) sentenceJson.get("string");
    }

}
