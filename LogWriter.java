import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

/**
 * Created by sergeybp on 03.11.16.
 */
public class LogWriter {

    LogWriter(){
        try {
            PrintWriter out = new PrintWriter(new FileWriter("easy_log"));
            out.write("");
            out.close();
        } catch (IOException e) {
            e.printStackTrace();
        }

    }

    public void write(String s){
        try{
            PrintWriter out = new PrintWriter(new FileWriter("easy_log", true));
            out.println(s);
            out.close();
        } catch (Exception e) {
            // do something
        }
    }

}
