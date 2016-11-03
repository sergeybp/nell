import net.uaprom.jmorphy2.MorphAnalyzer;
import net.uaprom.jmorphy2.ParsedWord;
import org.json.simple.JSONObject;

import java.io.IOException;

/**
 * Created by sergeybp on 27.10.16.
 */
public class SimpleWord {

    public static String puctuations = ".,&!?#\"\':;()";

    public boolean isPunctuation = false;
    public String pos;
    public String casee;
    public String lexem;
    public String number;
    public  String original;



    SimpleWord(String word, MorphAnalyzer analyzer) {
        if(word == null){
            return;
        }
        original = word;
        if(isPunctuation(word)){
            isPunctuation = true;
            lexem = word;
            return;
        }

        ParsedWord p = null;
        try {
            p = analyzer.parse(word).get(0);
        } catch (IOException e) {
            e.printStackTrace();
        }
        pos = p.tag.POS.toString();
        casee = p.tag.Case.toString();
        lexem = p.normalForm;
        number = p.tag.number.toString();

    }

    //TODO
    public static boolean isPunctuation(String word){
        for(int i = 0 ; i < puctuations.length(); i ++){
            if(word.equals(String.valueOf(puctuations.charAt(i)))){
                return true;
            }
        }
        return false;
    }

    public void fromJson(JSONObject wordJson){
        original = (String) wordJson.get("original");
        if((Boolean) wordJson.get("isPunctuation")){
            isPunctuation = true;
            lexem = original;
            return;
        }
        isPunctuation = false;
        pos = (String) wordJson.get("pos");
        if(pos == null){
            pos = "null";
        }
        casee = (String) wordJson.get("case");
        if(casee == null){
            casee = "null";
        }
        lexem = (String) wordJson.get("lexem");
        if(lexem == null){
            lexem = "null";
        }
        number = (String) wordJson.get("number");
        if(number == null){
            number = "null";
        }
    }



}

