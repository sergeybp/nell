import java.io.File;

/**
 * Created by sergeybp on 05.11.16.
 */
public class Tester {

    public static void main(String[] args){
        ProcessedText text = new ProcessedText();
        text.fromJson(new File("processed/text-corpus.part1.txt.json"));
        int a = 0;
        for(Sentence sentence : text.sentences){
            if(sentence.stringg.contains("кормов у взрослых")){
                a++;
            }

        }
        System.out.print(a);
    }

}
