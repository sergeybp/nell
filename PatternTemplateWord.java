import com.sun.istack.internal.NotNull;

/**
 * Created by sergeybp on 27.10.16.
 */
public class PatternTemplateWord {

    @NotNull
    String casee;
    @NotNull
    String number;
    @NotNull
    String pos;


    public PatternTemplateWord(String casee, String number, String pos) {
        this.casee = casee;
        this.number = number;
        this.pos = pos;
    }
}
