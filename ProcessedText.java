import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;


import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.Objects;

/**
 * Created by sergeybp on 28.10.16.
 */
public class ProcessedText {

    ArrayList<Sentence> sentences = new ArrayList<>();


    public ProcessedText(){

    }

    public void fromJson(File file){

        JSONParser parser = new JSONParser();

        try {

            Object obj = parser.parse(new FileReader(file));

            JSONObject obj1 = (JSONObject) obj;


            for (int i = 0 ; i < obj1.size(); i++) {
                Sentence sentence = new Sentence(null, null);
                sentence.fromJson((JSONObject) obj1.get(""+i));
                sentences.add(sentence);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

}

