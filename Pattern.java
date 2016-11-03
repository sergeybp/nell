/**
 * Created by sergeybp on 27.10.16.
 */
public class Pattern {

    int id;
    String pattern;
    PatternTemplateWord arg1;
    PatternTemplateWord arg2;


    public Pattern(int id, String pattern, PatternTemplateWord arg1, PatternTemplateWord arg2) {
        this.id = id;
        this.pattern = pattern;
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
}
